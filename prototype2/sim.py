"""The model layer, rebuilt on a global tick.

Time advances only through Game.step() -- one tick, everything at once:
ships ride their order queues, undecided water gnaws at components,
contracts age, buoys bill. step() returns the interrupts it generated;
the interrupt list is fixed and small, and it is the game's difficulty
dial, so nothing else may halt an advance.

One tick is half an hour of array time. Reality resolves where attention
is spent, and attention is singular: exactly one hull may hold the
observed flag.
"""
import json
import math
import os
import random
from collections import deque

import routes
import world

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'savegame.json')
SAVE_VERSION = 3

TICK_H = 0.5                  # hours per tick: speed in kts * TICK_H = NM/tick
REFRESH = 16                  # ticks between contract-offer rotations
RATE = (26, 55)               # $/NM a shipper pays, per item
ANOMALY_WAKES = 8             # tick after which something is out there

# observation
PORT_R, BUOY_R, FLAG_R = 9.0, 7.5, 9.0
DROPOUT_P = 0.04              # per-tick chance the observed flag yields nothing
BUOY_PRICE, BUOY_UPKEEP = 2500, 6           # $ and $/tick

# attrition: chance of a component hit per tick, indexed by *effective*
# stability 0..4 (water + the hull's own radar nudge)
DRIFT_P = (0.55, 0.38, 0.22, 0.10, 0.0)
DRIFT_DMG = (4, 12)           # damage per hit
REPAIR_TICKS_PER = 12         # damage points repaired per tick in a berth
REPAIR_COST_PER = 15          # $ per damage point

# emissions: every act of looking is an act of announcing
NOISE_DECAY = 8               # per tick
NOISE_ENGINE = 2              # per tick while underway
NOISE_PING = 30               # one active ping
NOISE_DRAWS = 25              # above this, the basin starts to listen

# the anomaly up close: indifferent, not hostile. The water there is so
# undecided that hulls corrupt and manifests stop being facts.
ANOM_RADIUS = 2.5             # NM
ANOM_HUL_P, ANOM_HUL_DMG = 0.7, (6, 14)
ANOM_VOID_P = 0.3             # per tick: one held contract deresolves
STAND_LOST = 4                # standing cost of cargo lost to the water
ANOM_JITTER = 14.0            # degrees the lying instrument is off by
ANOM_FLIP = (10, 20)          # ticks between the instruments trading honesty

# helm throttle stops: fraction of cruise speed, engine noise per tick,
# and the radar penalty for running hard
THROTTLES = ('STOP', 'SLOW', 'CRUISE', 'FLANK')
THR_SPEED = (0.0, 0.4, 1.0, 1.3)
THR_NOISE = (0, 1, 2, 6)
THR_RADAR = (1.0, 1.05, 1.0, 0.75)

# manage: at-sea jury-rigs are slow, expensive, and only ever half-measures
JURY_CAP = 60                 # a rig never restores past this
JURY_RATE = 6                 # damage points per tick
JURY_COST = 25                # $ per damage point

# agents automate labor, never attention
AGENT_PRICES = (None, 6000, 14000, 30000)
AGENT_STOP_NM = 4.0           # T1/T2 refuse a leg this close to the fix
AGENT_DIVERT_NM = 3.0         # T3 requires this much sea room

# the yard imports: some freight wants the unlit corridor
SHY_OFFER_P = 0.22

# standing
STAND_DELIVER, STAND_MISS = 2, 8
PRIORITY_STANDING = 65        # standing that unlocks priority contracts
MISS_PENALTY = 0.25           # fraction of payment forfeited on a missed window

CONTENTS = ["Salmon", "Bikes", "Wine", "Camping gear", "Boat parts",
            "Cat food", "Granola", "Hot peppers", "SCUBA gear", "Avocados",
            "Pasta", "Hard seltzers", "Guinness", "Transformers", "Cedar logs"]

CLASSES = {
    'Skiff':   dict(hold=[2, 3],       holdP=[7000],
                    spd=[12.0, 13.5],  spdP=[5000],
                    eff=[65, 55, 47],  effP=[4000, 6000],  price=18000),
    'Lighter': dict(hold=[4, 5, 6],    holdP=[12000, 18000],
                    spd=[9.0, 10.5, 12.0], spdP=[8000, 12000],
                    eff=[50, 40, 32],  effP=[5000, 9000],  price=46000),
    'Trawler': dict(hold=[6, 7, 8],    holdP=[15000, 22000],
                    spd=[7.5, 8.5, 9.5], spdP=[9000, 14000],
                    eff=[42, 34, 27],  effP=[7000, 11000], price=92000),
    'Cutter':  dict(hold=[3, 4],       holdP=[10000],
                    spd=[14.0, 16.0],  spdP=[9000],
                    eff=[58, 48, 40],  effP=[5000, 8000],  price=71000),
}

PORT_UPG = dict(cargo=([8, 10, 12, 14], [1200, 1600, 2200]),
                stage=([4, 6, 8], [3000, 5000]),
                docks=([2, 3], [15000]))

COMPONENTS = ('ENG', 'RDR', 'HUL')


class Contract:
    """A shipment with a window. The window ages every tick, everywhere.
    On the apron an expired offer just evaporates; in your custody an
    expired window is a miss -- penalty, standing, and the cargo decoheres
    into a VOID slot that rides along until the next docking."""

    def __init__(self, src, dest, contents, payment, window, priority=False):
        self.src, self.dest = src, dest
        self.contents, self.payment = contents, payment
        self.window, self.priority = window, priority
        self.void = False


class Port:
    def __init__(self, name, code, pos, shipyard=False):
        self.name, self.code, self.pos = name, code, pos
        self.shipyard = shipyard
        self.cargo, self.stage, self.ferries = [], [], []
        self.standing = 50
        self.lv = dict(cargo=0, stage=0, docks=0)
        if shipyard:
            self.lv['docks'] = 1

    def cap(self, kind):
        if self.shipyard and kind != 'docks':
            return dict(cargo=4, stage=2)[kind]   # the yard trades, modestly
        return PORT_UPG[kind][0][self.lv[kind]]

    def upgrade_price(self, kind):
        if self.shipyard and kind != 'docks':
            return None                   # the yard is what it is
        lvls, prices = PORT_UPG[kind]
        return prices[self.lv[kind]] if self.lv[kind] < len(lvls) - 1 else None

    def new_offer(self, game):
        dests = [p for p in game.cargo_ports() if p is not self]
        cap = self.cap('cargo')
        if self.standing < 25:
            cap = max(1, cap // 2)        # chronic lateness closes the economy
        if not dests or len(self.cargo) >= cap:
            return False
        # the yard imports parts and provisions -- freight with a reason
        # to sail the unlit corridor. The yard itself only ships out.
        if not self.shipyard and game.rng.random() < SHY_OFFER_P:
            d = game.shipyard()
        else:
            d = game.rng.choice(dests)
        dist = world.dist(self.pos, d.pos)
        pay = int(dist * game.rng.uniform(*RATE) / 5) * 5
        window = int(dist * 0.9) + game.rng.randint(8, 22)
        pri = self.standing >= PRIORITY_STANDING and game.rng.random() < 0.25
        if pri:
            pay, window = int(pay * 1.6 / 5) * 5, max(6, int(window * 0.55))
        self.cargo.append(Contract(self, d, game.rng.choice(CONTENTS),
                                   pay, window, pri))
        return True

    def sort_cargo(self):
        for lst in (self.cargo, self.stage):
            lst.sort(key=lambda c: (c.void, c.dest.code, -c.payment))

    def berths_free(self, game):
        """Docked hulls AND hulls already inbound both consume a berth."""
        inbound = sum(1 for f in game.ships
                      if f.queue and f.queue[0].get('dest') == self.code
                      and f.port is None)
        return self.cap('docks') - len(self.ferries) - inbound

    def bump_standing(self, d):
        self.standing = max(0, min(100, self.standing + d))


class Ship:
    def __init__(self, name, cls, port):
        self.name, self.cls = name, cls
        self.lv = dict(hold=0, spd=0, eff=0)
        self.cargo = []
        self.port = port                  # None while at sea
        self.pos = list(port.pos)
        self.heading = (1, 0)
        self.components = dict(ENG=100, RDR=100, HUL=100)
        self.power = dict(ENG=True, RDR=True)   # HUL is always in the water
        self.derelict = False
        self.noise = 0                    # emissions ledger, 0..100
        self.agent = 0                    # installed sub-AI tier, 0..3
        self.circuit = None               # dict(ports=[codes], paused=bool)
        self.queue = []                   # orders: plain dicts, save-ready
        port.ferries.append(self)

    # ---- stats ----------------------------------------------------------
    def stat(self, k):
        return CLASSES[self.cls][k][self.lv[k]]

    def hold_cap(self):
        return self.stat('hold')

    def speed(self):
        return self.stat('spd')

    def eff(self):
        return self.stat('eff')

    def speed_pt(self):
        """NM per tick, degraded by engine damage."""
        return self.stat('spd') * TICK_H * (0.3 + 0.7 * self.components['ENG'] / 100)

    def radar_r(self):
        if not self.power['RDR']:
            return 0.0
        r = 6.0 * (0.35 + 0.65 * self.components['RDR'] / 100)
        if self.queue and self.queue[0].get('kind') == 'helm':
            r *= THR_RADAR[self.queue[0]['thr']]
        return r

    def throttle(self):
        """Current helm throttle index, or None when not under manual helm."""
        if self.queue and self.queue[0].get('kind') == 'helm':
            return self.queue[0]['thr']
        return None

    def upgrade_price(self, k):
        arr = CLASSES[self.cls][k + 'P']
        return arr[self.lv[k]] if self.lv[k] < len(arr) else None

    # ---- orders ---------------------------------------------------------
    def _secure_helm(self, game):
        """A committed order supersedes the helm. A helm order stands until
        it is dropped, so a leg queued behind one would never be sailed."""
        if self.queue and self.queue[0]['kind'] == 'helm':
            self.queue.pop(0)
            game.log(f"{self.name} helm secured -- she has her orders")

    def enqueue_leg(self, option, dest_code, game):
        self._secure_helm(game)
        self.queue.append(dict(kind='leg', path=[list(p) for p in option.path],
                               nm=option.nm, done=0.0, dest=dest_code))
        if self.port is not None:
            self.port.ferries.remove(self)
            self.port = None
        game.log(f"{self.name} committed: {option.name} to {dest_code}, "
                 f"{option.nm:.1f} NM / {option.ticks(self.speed_pt())} ticks")

    def enqueue_repair(self, comp, game):
        dmg = 100 - self.components[comp]
        ticks = max(1, math.ceil(dmg / REPAIR_TICKS_PER))
        cost = dmg * REPAIR_COST_PER
        game.credits -= cost
        self.queue.append(dict(kind='repair', comp=comp, ticks=ticks))
        game.log(f"{self.name} repair {comp}: {ticks} ticks in the berth, -${cost:,}")

    def enqueue_tow(self, wreck, game):
        self._secure_helm(game)
        self.queue.append(dict(kind='tow', target=wreck.name, phase='out',
                               path=None, nm=0.0, done=0.0, dest=None))
        if self.port is not None:
            self.port.ferries.remove(self)
            self.port = None
        game.log(f"{self.name} away to take {wreck.name} under tow")

    def repair_quote(self, comp):
        dmg = 100 - self.components[comp]
        if dmg <= 0:
            return None
        return (max(1, math.ceil(dmg / REPAIR_TICKS_PER)), dmg * REPAIR_COST_PER)

    def jury_quote(self, comp):
        """(ticks, $) to rig comp back up to JURY_CAP at sea, or None."""
        pts = JURY_CAP - self.components[comp]
        if pts <= 0:
            return None
        return (max(1, math.ceil(pts / JURY_RATE)), pts * JURY_COST)

    def jury_rig(self, comp, game):
        q = self.jury_quote(comp)
        if q is None or self.port is not None or self.queue:
            return False
        game.credits -= q[1]
        self.queue.append(dict(kind='jury', comp=comp))
        game.log(f"{self.name} rigging {comp} at sea: to {JURY_CAP} at best, "
                 f"~{q[0]} ticks, -${q[1]:,}", 'a')
        return True

    def set_helm(self, hdg, thr, game):
        """Take the helm: heading in degrees, throttle stop 0..3. Replaces
        whatever the queue held -- orders are free, commitments are not."""
        if self.derelict:
            return
        if self.queue and self.queue[0].get('kind') == 'helm':
            self.queue[0]['hdg'], self.queue[0]['thr'] = hdg, thr
            return
        if any(o['kind'] == 'repair' for o in self.queue):
            game.log(f"{self.name} is opened up in a berth -- "
                     f"the yardbirds keep her helm", 'a')
            return
        self.queue = [dict(kind='helm', hdg=hdg, thr=thr)]
        if self.port is not None:
            self.port.ferries.remove(self)
            self.port = None
        game.log(f"{self.name} answers her helm -- "
                 f"hdg {int(hdg) % 360:03d}, {THROTTLES[thr]}")

    def drop_helm(self, game):
        if self.queue and self.queue[0].get('kind') == 'helm':
            self.queue.pop(0)
            game.log(f"{self.name} helm secured, holding position")

    def eta_ticks(self):
        """Ticks to clear the whole queue, as currently quoted."""
        t, spd = 0, max(0.01, self.speed_pt())
        for o in self.queue:
            if o['kind'] == 'leg':
                t += math.ceil((o['nm'] - o['done']) / spd)
            elif o['kind'] == 'repair':
                t += o['ticks']
        return t

    # ---- per-tick -------------------------------------------------------
    def tick(self, game, out):
        if not self.queue:
            self._agent_step(game, out)
            if not self.queue:
                return
        o = self.queue[0]
        if self.derelict and not (o['kind'] == 'repair' and self.port):
            return                        # a wreck can only be worked on ashore
        if o['kind'] == 'leg':
            self._tick_leg(o, game, out)
        elif o['kind'] == 'helm':
            self._tick_helm(o, game, out)
        elif o['kind'] == 'jury':
            v = min(JURY_CAP, self.components[o['comp']] + JURY_RATE)
            self.components[o['comp']] = v
            if v >= JURY_CAP:
                self.queue.pop(0)
                game.log(f"{self.name} {o['comp']} rigged to {v} -- "
                         f"it will hold, probably")
                if not self.queue:
                    out.append(('idle', f"{self.name} rig complete, holding"))
        elif o['kind'] == 'repair':
            o['ticks'] -= 1
            if o['ticks'] <= 0:
                self.components[o['comp']] = 100
                self.queue.pop(0)
                game.log(f"{self.name} {o['comp']} repaired to 100")
                if self.derelict and o['comp'] == 'HUL':
                    self.derelict = False
                    game.log(f"{self.name} answers her helm again", 'g')
                if not self.queue:
                    out.append(('idle', f"{self.name} idle at "
                                f"{self.port.code if self.port else 'sea'}"))
        elif o['kind'] == 'tow':
            self._tick_tow(o, game, out)

    def _advance(self, o, game, speed):
        step = min(speed, o['nm'] - o['done'])
        o['done'] += step
        game.credits -= step * self.eff()
        self.noise = min(100, self.noise + NOISE_ENGINE)
        old = tuple(self.pos)
        self.pos = list(routes.point_along(o['path'], o['done']))
        if abs(self.pos[0] - old[0]) + abs(self.pos[1] - old[1]) > 1e-6:
            self.heading = (self.pos[0] - old[0], self.pos[1] - old[1])
        return o['done'] >= o['nm'] - 1e-9

    def _tick_helm(self, o, game, out):
        thr = o['thr']
        if thr == 0 or not self.power['ENG']:
            return                        # lying quiet is a valid order
        spd = self.speed_pt() * THR_SPEED[thr]
        th = math.radians(o['hdg'])
        dx, dy = math.cos(th), math.sin(th)
        # look one step ahead: the helm refuses to put her ashore
        for frac in (0.5, 1.0):
            nx, ny = self.pos[0] + dx * spd * frac, self.pos[1] + dy * spd * frac
            if world.land(nx, ny) or not (0 <= nx < world.W and 0 <= ny < world.H):
                o['thr'] = 0
                game.log(f"{self.name} BREAKERS AHEAD -- all stop", 'a')
                out.append(('idle', f"{self.name} all stop at the shore"))
                return
        self.pos[0] += dx * spd
        self.pos[1] += dy * spd
        self.heading = (dx, dy)
        game.credits -= spd * self.eff()
        self.noise = min(100, self.noise + THR_NOISE[thr])

    def _tick_leg(self, o, game, out):
        if self._advance(o, game, self.speed_pt()):
            self.queue.pop(0)
            if o['dest'] is None:         # a leg into open water: hold here
                if not self.queue:
                    out.append(('idle', f"{self.name} holding in open water"))
            else:
                self._dock(game.port(o['dest']), game, out)

    def _tick_tow(self, o, game, out):
        wreck = game.ship(o['target'])
        if wreck is None or not wreck.derelict or wreck.port is not None:
            self.queue.pop(0)             # gone, revived, or already ashore
            out.append(('idle', f"{self.name} tow order lapsed"))
            return
        if o['phase'] == 'out':
            if o['path'] is None:
                # navigate straight to the wreck; it is not going anywhere
                o['path'] = [list(self.pos), list(wreck.pos)]
                o['nm'] = routes.path_len(o['path'])
                o['done'] = 0.0
            if self._advance(o, game, self.speed_pt()):
                yard = game.shipyard()
                opts = routes.options(tuple(self.pos), yard.code, game.stability)
                path = [list(p) for p in opts[0].path] if opts \
                    else [list(self.pos), list(yard.pos)]
                o.update(phase='back', path=path, nm=routes.path_len(path),
                         done=0.0, dest=yard.code)
                game.log(f"{self.name} has {wreck.name} under tow")
        else:
            if self._advance(o, game, self.speed_pt() * 0.5):
                self.queue.pop(0)
                yard = game.port(o['dest'])
                self._dock(yard, game, out)
                wreck.port = yard
                wreck.pos = list(yard.pos)
                yard.ferries.append(wreck)
                game.log(f"{wreck.name} towed into the yard -- "
                         f"derelict until her hull is rebuilt", 'a')
            else:
                wreck.pos = list(self.pos)

    def _dock(self, port, game, out):
        self.port = port
        self.pos = list(port.pos)
        port.ferries.append(self)
        self.cargo = [c for c in self.cargo if not c.void]   # voids clear ashore
        items = [c for c in self.cargo if c.dest is port and not c.void]
        if items:
            bonus = 1.0 + 0.05 * (len(items) - 1)
            pay = int(sum(c.payment for c in items) * bonus)
            for c in items:
                self.cargo.remove(c)
                c.src.bump_standing(STAND_DELIVER)
            game.credits += pay
            game.log(f"{self.name} docked {port.name}: {len(items)} delivered, "
                     f"+${pay:,}" + (f" (bundle x{bonus:.2f})" if len(items) > 1 else ""))
        else:
            game.log(f"{self.name} docked {port.name}")
        if not self.queue:
            out.append(('idle', f"{self.name} docked {port.code}, queue empty"))

    # ---- the installed sub-AI -------------------------------------------
    # Agents automate labor, never attention: they load, sail, and divert,
    # but an agent-run hull is as unobserved as any other and none of them
    # may ever hold the flag. Why they cannot observe is not for us to say.
    def _agent_step(self, game, out):
        cir = self.circuit
        if (self.agent < 1 or not cir or cir.get('paused') or self.derelict
                or len(cir['ports']) < 2):
            return
        ports = cir['ports']
        here = self.port.code if self.port else None
        if here in ports:
            nxt = ports[(ports.index(here) + 1) % len(ports)]
        else:
            nxt = min(ports, key=lambda c: world.dist(
                self.pos, game.port(c).pos))
            if here == nxt:               # docked off-circuit at the target
                nxt = ports[(ports.index(nxt) + 1) % len(ports)]
        dest = game.port(nxt)

        # tier 1 automates sailing, not lading: if there is circuit freight
        # on this apron and the hold is empty, she waits for dispatch
        if self.port is not None and self.agent == 1 \
                and not [c for c in self.cargo if not c.void] \
                and any(not c.void and c.dest.code in ports
                        and c.dest is not self.port
                        for c in self.port.cargo):
            return

        # tier 2+: full port operations -- load whatever serves the circuit
        if self.port is not None and self.agent >= 2:
            for c in sorted(self.port.cargo, key=lambda c: -c.payment):
                if len(self.cargo) >= self.hold_cap():
                    break
                if c.void or c.dest.code not in ports \
                        or c.dest is self.port:
                    continue
                self.port.cargo.remove(c)
                self.cargo.append(c)

        if dest.berths_free(game) <= 0:
            return                        # wait a tick; berths clear

        start = self.port.code if self.port else tuple(self.pos)
        opts = routes.options(start, dest.code, game.water_for(self))
        if not opts:
            self._agent_pause(game, out, 'no navigable route')
            return
        rep = game.anomaly_report()
        fix = rep[:2] if rep and rep[2] <= 4 else None

        def clearance(o):
            if fix is None:
                return 9e9
            return min(world.dist(p, fix) for p in routes.sample(o.path))

        if self.agent >= 3 and fix is not None:
            safe = [o for o in opts if clearance(o) > AGENT_DIVERT_NM]
            if not safe:
                self._agent_pause(game, out, 'no sea room around the contact')
                return
            o = safe[0]                   # already sorted most-stable first
            if clearance(opts[0]) <= AGENT_DIVERT_NM:
                game.log(f"{self.name} agent diverting around the fix", 'c')
        else:
            o = opts[0]
            if fix is not None and clearance(o) < AGENT_STOP_NM:
                self._agent_pause(game, out,
                                  'contact on the route -- stopping dead')
                return
        self.enqueue_leg(o, dest.code, game)

    def _agent_pause(self, game, out, why):
        self.circuit['paused'] = True
        game.log(f"{self.name} agent: {why}", 'a')
        out.append(('agent', f"{self.name} circuit paused"))

    # ---- attrition ------------------------------------------------------
    def drift_roll(self, game, out):
        if self.derelict or self.port is not None:
            return
        if game.observed is self and not game.dropout:
            s = 4                         # the flag: strongest collapse
        else:
            # own radar nudges the water -- partial collapse, never full
            s = game.stability(*self.pos, exclude=self)
            if self.power['RDR'] and self.components['RDR'] >= 30:
                s = min(4, s + 1)
        p = DRIFT_P[s]
        if p and game.rng.random() < p:
            # powered-down systems ride it out; the hull never can
            pool = ['HUL'] + [c for c in ('ENG', 'RDR') if self.power[c]]
            comp = game.rng.choice(pool)
            dmg = game.rng.randint(*DRIFT_DMG)
            self.components[comp] = max(0, self.components[comp] - dmg)
            game.log(f"{self.name} {comp} -{dmg} in undecided water "
                     f"({self.components[comp]} left)", 'a')
            out.append(('damage', f"{self.name} {comp} hit"))
            if self.agent == 1 and self.circuit \
                    and not self.circuit.get('paused'):
                self._agent_pause(game, out, 'damage -- nothing in the '
                                 'manual covers this')
            if self.components['HUL'] <= 0:
                self.go_derelict(game, out)

    def go_derelict(self, game, out):
        self.derelict = True
        self.queue.clear()
        game.abandon(self, why='lost with the hull')
        if game.observed is self:
            game.observed = None
        game.log(f"{self.name} DERELICT -- dead in the water, "
                 f"contracts decohered", 'm')
        out.append(('derelict', f"{self.name} derelict"))


class Anomaly:
    """Something the array has not decided. It is only ever *reported*
    where coverage reaches; elsewhere the board shows a stale last-known.

    Radar and sonar disagree about it, and at any moment exactly one of
    them is honest. Which one flips on its own schedule. A ping reveals
    the current truth; committing to a read without one is the Interpret
    verb's whole gamble."""

    def __init__(self):
        self.pos = [56.0, 26.0]
        self.drift = 0.7
        self.alive = False
        self.honest = 'radar'
        self.next_flip = 0

    def tick(self, game):
        if not self.alive:
            if game.tick_no >= ANOMALY_WAKES:
                self.alive = True
                self.honest = game.rng.choice(('radar', 'sonar'))
                self.next_flip = game.tick_no + game.rng.randint(*ANOM_FLIP)
            return
        if game.tick_no >= self.next_flip:
            self.honest = 'sonar' if self.honest == 'radar' else 'radar'
            self.next_flip = game.tick_no + game.rng.randint(*ANOM_FLIP)
        self.drift += game.rng.uniform(-0.4, 0.4)
        self.pos[0] += math.cos(self.drift) * 0.5
        self.pos[1] += math.sin(self.drift) * 0.5
        # Noise-drawn precursor: emissions are bait. A loud hull nearby
        # bends the wander toward it -- gently, for now.
        loud = [f for f in game.ships if not f.derelict
                and f.noise >= NOISE_DRAWS
                and world.dist(f.pos, self.pos) < 18]
        if loud:
            t = max(loud, key=lambda f: f.noise)
            d = world.dist(t.pos, self.pos)
            if d > 0.1:
                self.pos[0] += (t.pos[0] - self.pos[0]) / d * 0.35
                self.pos[1] += (t.pos[1] - self.pos[1]) / d * 0.35
        # it is undecidedness itself: decided water pushes it out. This is
        # also what keeps it from camping a port's doorstep forever.
        if game.stability(*self.pos) >= 3:
            near = min(game.ports, key=lambda p: world.dist(p.pos, self.pos))
            d = world.dist(near.pos, self.pos)
            if d > 0.1:
                self.pos[0] += (self.pos[0] - near.pos[0]) / d * 0.8
                self.pos[1] += (self.pos[1] - near.pos[1]) / d * 0.8
        self.pos[0] = max(44, min(70, self.pos[0]))
        self.pos[1] = max(20, min(31, self.pos[1]))


class Game:
    def __init__(self, seed=None):
        world.build()
        self.rng = random.Random(seed)
        self.ports = [Port("Mercer Island", "MER", routes.NODES['MER']),
                      Port("Edmonds", "EDM", routes.NODES['EDM']),
                      Port("Kingston", "KNG", routes.NODES['KNG']),
                      Port("Shipyard", "SHY", routes.NODES['SHY'], shipyard=True)]
        self.buoys = {'B1', 'B2', 'B3a', 'B3', 'B4', 'B5'}   # powered stations
        self.ships = [Ship("ENDURANCE", 'Lighter', self.ports[0]),
                      Ship("DISCOVERY", 'Skiff', self.ports[1])]
        self.credits = 10000
        self.in_arrears = False
        self.tick_no = 0
        self.observed = None              # the ship holding the flag, or None
        self.dropout = False              # flag failed this tick
        self.events = deque(maxlen=6)
        self.anomaly = Anomaly()
        self.anomaly_seen = None          # (x, y, tick) last covered sighting
        self.read = None                  # committed instrument: radar/sonar
        for p in self.ports:
            for _ in range(p.cap('cargo') // 2):
                p.new_offer(self)
            p.sort_cargo()
        self.log("array nominal. the freight keeps moving.")

    # ---- lookups --------------------------------------------------------
    def cargo_ports(self):
        return [p for p in self.ports if not p.shipyard]

    def shipyard(self):
        return self.ports[-1]

    def port(self, code):
        for p in self.ports:
            if p.code == code:
                return p
        raise KeyError(code)

    def ship(self, name):
        for f in self.ships:
            if f.name == name:
                return f
        return None

    def wrecks(self):
        return [f for f in self.ships if f.derelict and f.port is None]

    def log(self, msg, fg='_'):
        self.events.append((self.tick_no, msg, fg))

    def clock(self):
        return f"TICK {self.tick_no:04d}"

    # ---- observation ----------------------------------------------------
    def coverage(self, exclude=None):
        """(x, y, radius) of everything that collapses uncertainty."""
        out = [(p.pos[0], p.pos[1], PORT_R) for p in self.ports]
        out += [(routes.NODES[b][0], routes.NODES[b][1], BUOY_R)
                for b in self.buoys]
        for f in self.ships:
            if f.derelict or f is exclude:
                continue
            r = FLAG_R if (self.observed is f and not self.dropout) \
                else f.radar_r()
            if r > 0.01:                  # a dark array collapses nothing
                out.append((f.pos[0], f.pos[1], r))
        return out

    def stability(self, x, y, exclude=None):
        """0 (full superposition) .. 4 (decided). `exclude` drops one hull
        from coverage -- a ship never rates its own water by its own radar;
        that partial collapse is applied separately as a bonus."""
        best = 9e9
        for sx, sy, r in self.coverage(exclude):
            d = math.hypot(x - sx, y - sy) / r
            if d < best:
                best = d
        return 4 if best <= 0.6 else 3 if best <= 1.0 else \
            2 if best <= 1.35 else 1 if best <= 1.75 else 0

    def water_for(self, ship):
        """The stability function a hull's quotes and rolls are made
        against: the world as decided by everything except herself."""
        return lambda x, y: self.stability(x, y, exclude=ship)

    def anomaly_claims(self, f):
        """What f's instruments say about the anomaly, honestly or not.
        Returns dict(radar=(x, y), sonar_brg=radians, rng=NM) or None if
        she is too far off to register at all."""
        if not self.anomaly.alive or f.derelict:
            return None
        ax, ay = self.anomaly.pos
        r = world.dist(f.pos, (ax, ay))
        if r > max(4.0, f.radar_r() * 2.5) or r < 0.05:
            return None
        b = math.atan2(ay - f.pos[1], ax - f.pos[0])
        jit = math.radians(ANOM_JITTER + (self.tick_no * 7) % 5)
        if self.anomaly.honest == 'radar':
            radar = (ax, ay)
            sonar_brg = b - jit
        else:
            radar = (f.pos[0] + math.cos(b + jit) * r,
                     f.pos[1] + math.sin(b + jit) * r)
            sonar_brg = b
        return dict(radar=radar, sonar_brg=sonar_brg, rng=r)

    def anomaly_report(self):
        """(x, y, ticks_stale, tag) or None -- the board's working fix.
        Coverage resolves it outright; failing that, a committed Interpret
        read plots what one instrument claims; failing that, staleness."""
        if not self.anomaly.alive:
            return None
        if self.stability(*self.anomaly.pos) >= 2:
            return (self.anomaly.pos[0], self.anomaly.pos[1], 0, 'RESOLVED')
        if self.read:
            best = None
            for f in self.ships:
                c = self.anomaly_claims(f)
                if c and (best is None or c['rng'] < best[1]['rng']):
                    best = (f, c)
            if best:
                f, c = best
                if self.read == 'radar':
                    x, y = c['radar']
                else:
                    x = f.pos[0] + math.cos(c['sonar_brg']) * c['rng']
                    y = f.pos[1] + math.sin(c['sonar_brg']) * c['rng']
                return (x, y, 0, f'FIX/{self.read.upper()}')
        if self.anomaly_seen:
            x, y, t = self.anomaly_seen
            return (x, y, self.tick_no - t, 'LAST SEEN')
        return None

    def set_read(self, read):
        """Interpret: commit to an instrument. No confirmation is coming."""
        self.read = read
        self.log(f"read committed: {read.upper()} is to be believed"
                 if read else "read withheld -- the plot goes stale", 'c')

    # ---- player actions -------------------------------------------------
    def set_observed(self, ship):
        self.observed = None if self.observed is ship else ship
        if self.observed:
            self.log(f"observed flag on {ship.name} -- "
                     f"the array attends to her water")
        else:
            self.log("observed flag struck")

    def ping(self, ship):
        """One active ping: full resolution for the asker, and everything
        else in the water now knows exactly where she is. If the anomaly is
        in earshot, the echo also settles which instrument has been honest
        -- until the disagreement drifts again."""
        ship.noise = min(100, ship.noise + NOISE_PING)
        if self.anomaly_claims(ship):
            self.log(f"{ship.name} PINGS -- echo confirms "
                     f"{self.anomaly.honest.upper()} has been honest", 'a')
        else:
            self.log(f"{ship.name} PINGS -- the water answers, and listens", 'a')

    def abandon(self, ship, why='abandoned'):
        """Void every contract aboard. Standing cost scales with progress --
        the further along, the worse the breach."""
        total = 0
        for c in ship.cargo:
            if c.void:
                continue
            full = world.dist(c.src.pos, c.dest.pos)
            prog = 1.0 - min(1.0, world.dist(ship.pos, c.dest.pos) / full) \
                if full else 0.0
            cost = 6 + int(12 * prog)
            c.src.bump_standing(-cost)
            total += cost
            c.void = True
        if total:
            self.log(f"contracts {why}: hold decoheres, standing -{total}", 'a')
        return total

    def buy_buoy(self, node, game_log=True):
        if node in self.buoys or node in routes.PORTS:
            return False
        if self.credits < BUOY_PRICE or self.in_arrears:
            return False
        self.credits -= BUOY_PRICE
        self.buoys.add(node)
        if game_log:
            self.log(f"buoy tender away -- station {node} lit, "
                     f"-${BUOY_PRICE:,} and ${BUOY_UPKEEP}/tick")
        return True

    # ---- the tick -------------------------------------------------------
    def step(self):
        """Advance one tick. Returns the list of (kind, msg) interrupts."""
        out = []
        self.tick_no += 1

        # the flag can fail: the player is an AI, and no position is safe
        was = self.dropout
        self.dropout = bool(self.observed) and self.rng.random() < DROPOUT_P
        if self.dropout and not was:
            self.log("OBSERVED FLAG DROPOUT -- the array blinked", 'm')
            out.append(('dropout', 'flag dropout'))

        for f in self.ships:
            f.noise = max(0, f.noise - NOISE_DECAY)
        for f in self.ships:
            f.tick(self, out)
        for f in self.ships:
            f.drift_roll(self, out)

        # the anomaly moves; the board only knows what coverage tells it
        rep = self.anomaly_report()
        was_seen = rep is not None and rep[3] == 'RESOLVED'
        self.anomaly.tick(self)
        if self.anomaly.alive:
            if self.stability(*self.anomaly.pos) >= 2:
                if not was_seen:
                    self.log("anomalous return in the southern basin -- "
                             "radar/sonar disagree", 'm')
                    out.append(('contact', 'anomaly in coverage'))
                self.anomaly_seen = (self.anomaly.pos[0], self.anomaly.pos[1],
                                     self.tick_no)

            # up close, the water is too undecided to carry facts: hulls
            # corrupt and manifests deresolve. Indifferent, not hostile.
            for f in self.ships:
                if f.derelict or f.port is not None:
                    continue
                if world.dist(f.pos, self.anomaly.pos) > ANOM_RADIUS:
                    continue
                if self.rng.random() < ANOM_HUL_P:
                    dmg = self.rng.randint(*ANOM_HUL_DMG)
                    f.components['HUL'] = max(0, f.components['HUL'] - dmg)
                    self.log(f"the water refuses {f.name}: hull -{dmg} "
                             f"({f.components['HUL']} left)", 'm')
                    out.append(('anomaly', f"{f.name} in the undecided water"))
                    if f.circuit and not f.circuit.get('paused'):
                        f._agent_pause(self, out, 'inside the contact -- '
                                       'all judgment returned to dispatch')
                    if f.components['HUL'] <= 0:
                        f.go_derelict(self, out)
                        continue
                live = [c for c in f.cargo if not c.void]
                if live and self.rng.random() < ANOM_VOID_P:
                    c = self.rng.choice(live)
                    c.void = True
                    c.src.bump_standing(-STAND_LOST)
                    self.log(f"{c.contents} aboard {f.name} DERESOLVES -- "
                             f"the manifest no longer agrees it exists", 'm')
                    out.append(('anomaly', f"cargo deresolved aboard {f.name}"))

        # contracts age everywhere; custody makes expiry a miss
        for p in self.ports:
            for c in list(p.cargo):
                c.window -= 1
                if c.window <= 0:
                    p.cargo.remove(c)     # unclaimed offer evaporates
            for c in list(p.stage):
                c.window -= 1
                if c.window <= 0:
                    self._miss(c, out)
                    p.stage.remove(c)
        for f in self.ships:
            for c in f.cargo:
                if c.void:
                    continue
                c.window -= 1
                if c.window <= 0:
                    self._miss(c, out)
                    c.void = True
                elif c.window == 3:
                    out.append(('window', f"{c.contents} window at 3"))
                    self.log(f"{c.contents} for {c.dest.code}: "
                             f"3 ticks on the window", 'a')

        if self.tick_no % REFRESH == 0:
            for p in self.ports:
                for c in list(p.cargo):
                    if self.rng.random() < 0.25:
                        p.cargo.remove(c)
                target = p.cap('cargo') * 3 // 4
                while len(p.cargo) < target:
                    if not p.new_offer(self):
                        break
                p.sort_cargo()
            self.log("shippers rotated their manifests")

        self.credits -= BUOY_UPKEEP * len(self.buoys)

        # Arrears are allowed -- you can dig a hole -- but they are announced.
        if self.credits < 0 and not self.in_arrears:
            self.in_arrears = True
            self.log("ACCOUNTS IN ARREARS -- no refits or purchases until clear", 'a')
        elif self.credits >= 0 and self.in_arrears:
            self.in_arrears = False
            self.log("accounts clear")
        return out

    def _miss(self, c, out):
        pen = int(c.payment * MISS_PENALTY)
        self.credits -= pen
        c.src.bump_standing(-STAND_MISS)
        self.log(f"window MISSED on {c.contents} for {c.dest.code}: "
                 f"-${pen:,}, standing -{STAND_MISS}", 'a')

    # ---- persistence ----------------------------------------------------
    # Geography, lanes, and port layout are deterministic; a save is only
    # the mutable state. Orders are already plain dicts, so the queue
    # serializes as-is.
    def save(self, path=SAVE_PATH):
        def cargo(lst):
            return [[c.src.code, c.dest.code, c.contents, c.payment,
                     c.window, c.priority, c.void] for c in lst]

        data = dict(
            version=SAVE_VERSION,
            tick_no=self.tick_no, credits=self.credits,
            in_arrears=self.in_arrears,
            observed=self.observed.name if self.observed else None,
            dropout=self.dropout,
            buoys=sorted(self.buoys),
            events=[list(e) for e in self.events],
            anomaly=dict(pos=self.anomaly.pos, drift=self.anomaly.drift,
                         alive=self.anomaly.alive, honest=self.anomaly.honest,
                         next_flip=self.anomaly.next_flip),
            anomaly_seen=list(self.anomaly_seen) if self.anomaly_seen else None,
            read=self.read,
            rng=self.rng.getstate(),
            ports={p.code: dict(lv=p.lv, standing=p.standing,
                                cargo=cargo(p.cargo), stage=cargo(p.stage))
                   for p in self.ports},
            ships=[dict(name=f.name, cls=f.cls, lv=f.lv, cargo=cargo(f.cargo),
                        port=f.port.code if f.port else None,
                        pos=f.pos, heading=list(f.heading),
                        components=f.components, derelict=f.derelict,
                        noise=f.noise, power=f.power, agent=f.agent,
                        circuit=f.circuit, queue=f.queue)
                   for f in self.ships])
        tmp = path + '.tmp'
        with open(tmp, 'w') as fp:
            json.dump(data, fp, indent=1)
        os.replace(tmp, path)


def load(path=SAVE_PATH):
    """Rebuild a Game from a snapshot. Missing file raises FileNotFoundError;
    an incompatible save fails loudly rather than half-loading."""
    with open(path) as fp:
        data = json.load(fp)
    if data.get('version') != SAVE_VERSION:
        raise ValueError(f"save is version {data.get('version')}, "
                         f"this build reads {SAVE_VERSION}")

    g = Game()
    by_code = {p.code: p for p in g.ports}
    for p in g.ports:                     # drop the fresh-game seed state
        p.cargo.clear(); p.stage.clear(); p.ferries.clear()
    g.ships.clear()
    g.events.clear()

    def cargo(lst):
        out = []
        for s, d, contents, pay, window, pri, void in lst:
            c = Contract(by_code[s], by_code[d], contents, pay, window, pri)
            c.void = void
            out.append(c)
        return out

    g.tick_no, g.credits = data['tick_no'], data['credits']
    g.in_arrears, g.dropout = data['in_arrears'], data['dropout']
    g.buoys = set(data['buoys'])
    g.events.extend(tuple(e) for e in data['events'])
    st = data['rng']
    g.rng.setstate((st[0], tuple(st[1]), st[2]))
    g.anomaly.pos = list(data['anomaly']['pos'])
    g.anomaly.drift = data['anomaly']['drift']
    g.anomaly.alive = data['anomaly']['alive']
    g.anomaly.honest = data['anomaly']['honest']
    g.anomaly.next_flip = data['anomaly']['next_flip']
    g.anomaly_seen = tuple(data['anomaly_seen']) if data['anomaly_seen'] else None
    g.read = data['read']
    for code, pd in data['ports'].items():
        p = by_code[code]
        p.lv.update(pd['lv'])
        p.standing = pd['standing']
        p.cargo = cargo(pd['cargo'])
        p.stage = cargo(pd['stage'])
    for fd in data['ships']:
        home = by_code[fd['port']] if fd['port'] else g.ports[0]
        f = Ship(fd['name'], fd['cls'], home)
        if fd['port'] is None:
            home.ferries.remove(f)        # at sea, not berthed
            f.port = None
        f.lv.update(fd['lv'])
        f.cargo = cargo(fd['cargo'])
        f.pos = list(fd['pos'])
        f.heading = tuple(fd['heading'])
        f.components = dict(fd['components'])
        f.derelict = fd['derelict']
        f.noise = fd['noise']
        f.power = dict(fd['power'])
        f.agent = fd['agent']
        f.circuit = fd['circuit']
        f.queue = fd['queue']
        g.ships.append(f)
    g.observed = g.ship(data['observed']) if data['observed'] else None
    g.log("state restored from disk")
    return g
