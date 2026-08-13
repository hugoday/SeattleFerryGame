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
SAVE_VERSION = 2

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
        return PORT_UPG[kind][0][self.lv[kind]] if not self.shipyard or kind == 'docks' \
            else 0

    def upgrade_price(self, kind):
        lvls, prices = PORT_UPG[kind]
        return prices[self.lv[kind]] if self.lv[kind] < len(lvls) - 1 else None

    def new_offer(self, game):
        dests = [p for p in game.cargo_ports() if p is not self]
        cap = self.cap('cargo')
        if self.standing < 25:
            cap = max(1, cap // 2)        # chronic lateness closes the economy
        if not dests or len(self.cargo) >= cap:
            return False
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
        self.derelict = False
        self.noise = 0                    # emissions ledger, 0..100
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
        return 6.0 * (0.35 + 0.65 * self.components['RDR'] / 100)

    def upgrade_price(self, k):
        arr = CLASSES[self.cls][k + 'P']
        return arr[self.lv[k]] if self.lv[k] < len(arr) else None

    # ---- orders ---------------------------------------------------------
    def enqueue_leg(self, option, dest_code, game):
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
            return
        o = self.queue[0]
        if self.derelict and not (o['kind'] == 'repair' and self.port):
            return                        # a wreck can only be worked on ashore
        if o['kind'] == 'leg':
            self._tick_leg(o, game, out)
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
        if wreck is None or not wreck.derelict:
            self.queue.pop(0)             # nothing left to tow
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
                best = opts[0]
                o.update(phase='back', path=[list(p) for p in best.path],
                         nm=best.nm, done=0.0, dest=yard.code)
                game.log(f"{self.name} has {wreck.name} under tow")
        else:
            if self._advance(o, game, self.speed_pt() * 0.5):
                wreck.pos = list(self.pos)
                self.queue.pop(0)
                yard = game.port(o['dest'])
                self._dock(yard, game, out)
                wreck.port = yard
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

    # ---- attrition ------------------------------------------------------
    def drift_roll(self, game, out):
        if self.derelict or self.port is not None:
            return
        if game.observed is self and not game.dropout:
            s = 4                         # the flag: strongest collapse
        else:
            # own radar nudges the water -- partial collapse, never full
            s = game.stability(*self.pos, exclude=self)
            if self.components['RDR'] >= 30:
                s = min(4, s + 1)
        p = DRIFT_P[s]
        if p and game.rng.random() < p:
            comp = game.rng.choice(COMPONENTS)
            dmg = game.rng.randint(*DRIFT_DMG)
            self.components[comp] = max(0, self.components[comp] - dmg)
            game.log(f"{self.name} {comp} -{dmg} in undecided water "
                     f"({self.components[comp]} left)", 'a')
            out.append(('damage', f"{self.name} {comp} hit"))
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
    where coverage reaches; elsewhere the board shows a stale last-known."""

    def __init__(self):
        self.pos = [56.0, 26.0]
        self.drift = 0.7
        self.alive = False

    def tick(self, game):
        if not self.alive:
            if game.tick_no >= ANOMALY_WAKES:
                self.alive = True
            return
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
        for p in self.cargo_ports():
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

    def anomaly_report(self):
        """(x, y, ticks_stale) or None -- what the board may honestly show."""
        if not self.anomaly.alive:
            return None
        if self.stability(*self.anomaly.pos) >= 2:
            return (self.anomaly.pos[0], self.anomaly.pos[1], 0)
        if self.anomaly_seen:
            x, y, t = self.anomaly_seen
            return (x, y, self.tick_no - t)
        return None

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
        else in the water now knows exactly where she is."""
        ship.noise = min(100, ship.noise + NOISE_PING)
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
        was_seen = self.anomaly_report() is not None and \
            self.anomaly_report()[2] == 0
        self.anomaly.tick(self)
        if self.anomaly.alive:
            if self.stability(*self.anomaly.pos) >= 2:
                if not was_seen:
                    self.log("anomalous return in the southern basin -- "
                             "radar/sonar disagree", 'm')
                    out.append(('contact', 'anomaly in coverage'))
                self.anomaly_seen = (self.anomaly.pos[0], self.anomaly.pos[1],
                                     self.tick_no)

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
            for p in self.cargo_ports():
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
                         alive=self.anomaly.alive),
            anomaly_seen=list(self.anomaly_seen) if self.anomaly_seen else None,
            rng=self.rng.getstate(),
            ports={p.code: dict(lv=p.lv, standing=p.standing,
                                cargo=cargo(p.cargo), stage=cargo(p.stage))
                   for p in self.ports},
            ships=[dict(name=f.name, cls=f.cls, lv=f.lv, cargo=cargo(f.cargo),
                        port=f.port.code if f.port else None,
                        pos=f.pos, heading=list(f.heading),
                        components=f.components, derelict=f.derelict,
                        noise=f.noise, queue=f.queue)
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
    g.anomaly_seen = tuple(data['anomaly_seen']) if data['anomaly_seen'] else None
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
        f.queue = fd['queue']
        g.ships.append(f)
    g.observed = g.ship(data['observed']) if data['observed'] else None
    g.log("state restored from disk")
    return g
