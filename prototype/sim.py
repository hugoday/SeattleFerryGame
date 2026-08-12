"""The model layer. Runs on world coordinates and game-hours; never pauses.

Money has teeth here: fuel burns per NM continuously, payments scale with
distance, and every upgrade is a real trade against the fuel bill.
"""
import json
import math
import os
import random
from collections import deque

import world

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'savegame.json')
SAVE_VERSION = 1
TIME_SCALE = 0.10            # game-hours per real second
JOB_PERIOD = 8.0             # hours between job refreshes
RATE = (26, 55)              # $/NM a shipper pays, per item

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


class Cargo:
    def __init__(self, src, dest, contents, payment):
        self.src, self.dest = src, dest
        self.contents, self.payment = contents, payment


class Port:
    def __init__(self, name, code, pos, shipyard=False):
        self.name, self.code, self.pos = name, code, pos
        self.shipyard = shipyard
        self.cargo, self.stage, self.ferries = [], [], []
        self.lv = dict(cargo=0, stage=0, docks=0)
        if shipyard:
            self.lv['docks'] = 1

    def cap(self, kind):
        return PORT_UPG[kind][0][self.lv[kind]] if not self.shipyard or kind == 'docks' \
            else 0

    def upgrade_price(self, kind):
        lvls, prices = PORT_UPG[kind]
        return prices[self.lv[kind]] if self.lv[kind] < len(lvls) - 1 else None

    def new_job(self, game):
        dests = [p for p in game.cargo_ports() if p is not self]
        if not dests or len(self.cargo) >= self.cap('cargo'):
            return False
        d = random.choice(dests)
        pay = int(world.dist(self.pos, d.pos) * random.uniform(*RATE) / 5) * 5
        self.cargo.append(Cargo(self, d, random.choice(CONTENTS), pay))
        return True

    def sort_cargo(self):
        for lst in (self.cargo, self.stage):
            lst.sort(key=lambda c: (c.dest.code, -c.payment))

    def berths_free(self, game):
        """Docked hulls AND hulls already inbound both consume a berth."""
        inbound = sum(1 for f in game.ferries if f.moving and f.dest is self)
        return self.cap('docks') - len(self.ferries) - inbound


class Ferry:
    def __init__(self, name, cls, port):
        self.name, self.cls = name, cls
        self.lv = dict(hold=0, spd=0, eff=0)
        self.cargo = []
        self.port, self.dest = port, None
        self.pos = list(port.pos)
        self.moving = False
        self.traveled = self.trip_len = 0.0
        port.ferries.append(self)
        self.heading = (1, 0)

    # ---- stats ----------------------------------------------------------
    def stat(self, k):
        return CLASSES[self.cls][k][self.lv[k]]

    def hold_cap(self):
        return self.stat('hold')

    def speed(self):
        return self.stat('spd')

    def eff(self):
        return self.stat('eff')

    def upgrade_price(self, k):
        arr = CLASSES[self.cls][k + 'P']
        return arr[self.lv[k]] if self.lv[k] < len(arr) else None

    # ---- motion ---------------------------------------------------------
    def depart(self, dest, game):
        if self is None or dest is self.port:
            return
        self.dest = dest
        self.trip_len = world.dist(self.port.pos, dest.pos)
        self.traveled = 0.0
        self.origin = tuple(self.port.pos)
        if self in self.port.ferries:
            self.port.ferries.remove(self)
        self.moving = True
        dx, dy = dest.pos[0] - self.origin[0], dest.pos[1] - self.origin[1]
        self.heading = (dx, dy)
        game.log(f"{self.name} away for {dest.name}, "
                 f"{self.trip_len:.1f} NM, hold {len(self.cargo)}/{self.hold_cap()}")

    def eta_h(self):
        return (self.trip_len - self.traveled) / self.speed() if self.moving else 0.0

    def tick(self, dt_h, game):
        if not self.moving:
            return
        step = min(self.speed() * dt_h, self.trip_len - self.traveled)
        self.traveled += step
        game.credits -= step * self.eff()
        t = self.traveled / self.trip_len if self.trip_len else 1.0
        self.pos[0] = self.origin[0] + (self.dest.pos[0] - self.origin[0]) * t
        self.pos[1] = self.origin[1] + (self.dest.pos[1] - self.origin[1]) * t
        if self.traveled >= self.trip_len - 1e-9:
            self.arrive(game)

    def arrive(self, game):
        self.moving = False
        self.port = self.dest
        self.dest = None
        self.pos = list(self.port.pos)
        self.port.ferries.append(self)
        items = [c for c in self.cargo if c.dest is self.port]
        if items:
            bonus = 1.0 + 0.05 * (len(items) - 1)
            pay = int(sum(c.payment for c in items) * bonus)
            for c in items:
                self.cargo.remove(c)
            game.credits += pay
            game.log(f"{self.name} docked {self.port.name}: {len(items)} delivered, "
                     f"+${pay:,}" + (f" (bundle x{bonus:.2f})" if len(items) > 1 else ""))
        else:
            game.log(f"{self.name} docked {self.port.name}, nothing to deliver")


class Anomaly:
    """Something the array has not decided. For now it only exists."""

    def __init__(self):
        self.pos = [58.0, 26.0]
        self.drift = random.uniform(0, 2 * math.pi)
        self.alive = False

    def tick(self, dt_h, game):
        if not self.alive:
            if game.t > 4.0:
                self.alive = True
                game.log("anomalous return near the KNG corridor -- "
                         "radar/sonar disagree", 'm')
            return
        self.drift += random.uniform(-0.4, 0.4) * dt_h
        self.pos[0] += math.cos(self.drift) * 0.8 * dt_h
        self.pos[1] += math.sin(self.drift) * 0.8 * dt_h
        self.pos[0] = max(46, min(70, self.pos[0]))
        self.pos[1] = max(20, min(31, self.pos[1]))


class Game:
    def __init__(self):
        world.build()
        self.ports = [Port("Mercer Island", "MER", (20, 18)),
                      Port("Edmonds", "EDM", (40, 21)),
                      Port("Kingston", "KNG", (72, 14)),
                      Port("Shipyard", "SHY", (94, 22), shipyard=True)]
        self.buoys = [(30, 20), (34, 17), (50, 18), (58, 16), (65, 15)]
        self.routes = [((20, 18), (30, 20), '═'), ((30, 20), (34, 17), '═'),
                       ((34, 17), (40, 21), '═'), ((40, 21), (50, 18), '─'),
                       ((50, 18), (58, 16), '─'), ((58, 16), (65, 15), '─'),
                       ((65, 15), (72, 14), '─'), ((72, 14), (80, 18), '·'),
                       ((80, 18), (88, 20), '·'), ((88, 20), (94, 22), '·')]
        self.ferries = [Ferry("ENDURANCE", 'Lighter', self.ports[0]),
                        Ferry("DISCOVERY", 'Skiff', self.ports[1])]
        self.credits = 10000
        self.in_arrears = False
        self.t = 0.0
        self.next_jobs = JOB_PERIOD
        self.events = deque(maxlen=6)
        self.anomaly = Anomaly()
        for p in self.cargo_ports():
            for _ in range(p.cap('cargo') // 2):
                p.new_job(self)
            p.sort_cargo()
        self.log("array nominal. the freight keeps moving.")

    # ---- helpers --------------------------------------------------------
    def cargo_ports(self):
        return [p for p in self.ports if not p.shipyard]

    def shipyard(self):
        return self.ports[-1]

    def log(self, msg, fg='_'):
        self.events.append((self.t, msg, fg))

    def clock(self):
        return f"T+{int(self.t):02d}:{int(self.t % 1 * 60):02d}"

    def coverage(self):
        """(x, y, radius) of everything that collapses uncertainty."""
        out = [(p.pos[0], p.pos[1], 9.0) for p in self.ports]
        out += [(b[0], b[1], 5.0) for b in self.buoys]
        out += [(f.pos[0], f.pos[1], 6.0) for f in self.ferries]
        return out

    def uncertainty(self, x, y):
        best = 9e9
        for sx, sy, r in self.coverage():
            d = math.hypot(x - sx, y - sy) / r
            if d < best:
                best = d
        return best

    # ---- tick -----------------------------------------------------------
    def tick(self, dt_s):
        dt_h = dt_s * TIME_SCALE
        self.t += dt_h
        for f in self.ferries:
            f.tick(dt_h, self)
        self.anomaly.tick(dt_h, self)
        if self.t >= self.next_jobs:
            self.next_jobs += JOB_PERIOD
            for p in self.cargo_ports():
                for c in list(p.cargo):
                    if random.random() < 0.25:
                        p.cargo.remove(c)
                target = p.cap('cargo') * 3 // 4
                while len(p.cargo) < target:
                    if not p.new_job(self):      # no valid destination: stop
                        break
                p.sort_cargo()
            self.log("shippers rotated their manifests")
        # Arrears are allowed -- you can dig a hole -- but they are announced.
        if self.credits < 0 and not self.in_arrears:
            self.in_arrears = True
            self.log("ACCOUNTS IN ARREARS -- no refits or purchases until clear", 'a')
        elif self.credits >= 0 and self.in_arrears:
            self.in_arrears = False
            self.log("accounts clear")

    # ---- persistence ------------------------------------------------------
    # Geography and port layout are deterministic, so a save is only the
    # mutable state: the clock, the books, every manifest, every hull.
    # Cargo lives in exactly one list at a time and ports are keyed by code,
    # which keeps the snapshot flat.
    def save(self, path=SAVE_PATH):
        def cargo(lst):
            return [[c.src.code, c.dest.code, c.contents, c.payment] for c in lst]

        data = dict(
            version=SAVE_VERSION,
            t=self.t, credits=self.credits, in_arrears=self.in_arrears,
            next_jobs=self.next_jobs,
            events=[list(e) for e in self.events],
            anomaly=dict(pos=self.anomaly.pos, drift=self.anomaly.drift,
                         alive=self.anomaly.alive),
            ports={p.code: dict(lv=p.lv, cargo=cargo(p.cargo),
                                stage=cargo(p.stage)) for p in self.ports},
            ferries=[dict(name=f.name, cls=f.cls, lv=f.lv, cargo=cargo(f.cargo),
                          port=f.port.code, pos=f.pos, heading=list(f.heading),
                          moving=f.moving,
                          **(dict(dest=f.dest.code, origin=list(f.origin),
                                  traveled=f.traveled, trip_len=f.trip_len)
                             if f.moving else {}))
                     for f in self.ferries])
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
    g.ferries.clear()
    g.events.clear()

    def cargo(lst):
        return [Cargo(by_code[s], by_code[d], contents, pay)
                for s, d, contents, pay in lst]

    g.t, g.credits = data['t'], data['credits']
    g.in_arrears, g.next_jobs = data['in_arrears'], data['next_jobs']
    g.events.extend(tuple(e) for e in data['events'])
    g.anomaly.pos = list(data['anomaly']['pos'])
    g.anomaly.drift = data['anomaly']['drift']
    g.anomaly.alive = data['anomaly']['alive']
    for code, pd in data['ports'].items():
        p = by_code[code]
        p.lv.update(pd['lv'])
        p.cargo = cargo(pd['cargo'])
        p.stage = cargo(pd['stage'])
    for fd in data['ferries']:
        f = Ferry(fd['name'], fd['cls'], by_code[fd['port']])
        f.lv.update(fd['lv'])
        f.cargo = cargo(fd['cargo'])
        f.pos = list(fd['pos'])
        f.heading = tuple(fd['heading'])
        if fd['moving']:
            f.port.ferries.remove(f)      # at sea, not berthed
            f.moving = True
            f.dest = by_code[fd['dest']]
            f.origin = tuple(fd['origin'])
            f.traveled, f.trip_len = fd['traveled'], fd['trip_len']
        g.ferries.append(f)
    g.log("state restored from disk")
    return g
