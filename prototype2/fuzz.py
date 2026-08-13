"""Invariant fuzzer: random dispatcher behavior, hard assertions per tick.

Run:  python fuzz.py [seeds] [ticks]
Slower than checks.py; run it after structural changes to the model layer.
Asserts: berth lists never hold duplicates, every ship is docked in exactly
the port it claims (or none), every contract lives in exactly one container,
components and noise stay in range, derelicts hold no live cargo, and a
save/load round-trip mid-chaos changes nothing.
"""
import os
import random
import sys

import routes
import sim
import world

SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fuzz_save.json')


def invariants(g, tick, seed):
    where = f"seed {seed} tick {tick}"
    for p in g.ports:
        assert len(p.ferries) == len(set(id(x) for x in p.ferries)), \
            f"{where}: duplicate ship in {p.code}.ferries"
    for f in g.ships:
        homes = [p.code for p in g.ports if f in p.ferries]
        if f.port is not None:
            assert homes == [f.port.code], \
                f"{where}: {f.name} port={f.port.code} but berthed in {homes}"
        else:
            assert not homes, f"{where}: {f.name} at sea but berthed in {homes}"
        for c, v in f.components.items():
            assert 0 <= v <= 100, f"{where}: {f.name} {c}={v}"
        assert 0 <= f.noise <= 100, f"{where}: noise {f.noise}"
        assert all(o['kind'] in ('leg', 'helm', 'jury', 'repair', 'tow')
                   for o in f.queue), f"{where}: bad order kind"
        if f.derelict:
            assert not [c for c in f.cargo if not c.void], \
                f"{where}: derelict {f.name} holds live cargo"
    seen = set()
    for holder in g.ports:
        for c in holder.cargo + holder.stage:
            assert id(c) not in seen, f"{where}: contract in two places"
            seen.add(id(c))
    for f in g.ships:
        for c in f.cargo:
            assert id(c) not in seen, f"{where}: contract in two places"
            seen.add(id(c))
    assert abs(g.credits) < 1e9, f"{where}: credits blew up {g.credits}"


def act(g, rng):
    f = rng.choice(g.ships)
    r = rng.random()
    if r < 0.18 and not f.derelict:
        cands = [p for p in g.ports if p is not f.port]
        dest = rng.choice(cands)
        start = f.port.code if f.port else tuple(f.pos)
        opts = routes.options(start, dest.code, g.water_for(f))
        if opts and dest.berths_free(g) > 0 and not f.queue:
            f.enqueue_leg(rng.choice(opts), dest.code, g)
    elif r < 0.26 and not f.derelict:
        f.set_helm(rng.uniform(0, 360), rng.randint(0, 3), g)
    elif r < 0.30:
        f.drop_helm(g)
    elif r < 0.36 and not f.derelict:
        g.set_observed(f)
    elif r < 0.40:
        f.power['ENG'] = rng.random() < 0.8
        f.power['RDR'] = rng.random() < 0.8
    elif r < 0.44 and not f.derelict:
        g.ping(f)
    elif r < 0.48:
        g.set_read(rng.choice([None, 'radar', 'sonar']))
    elif r < 0.53 and f.port and not f.derelict:
        if f.port.cargo and len(f.cargo) < f.hold_cap():
            c = rng.choice(f.port.cargo)
            f.port.cargo.remove(c)
            f.cargo.append(c)
    elif r < 0.57:
        g.abandon(f)
    elif r < 0.62 and f.port and not f.queue:
        comp = rng.choice(('ENG', 'RDR', 'HUL'))
        if f.repair_quote(comp):
            f.enqueue_repair(comp, g)
    elif r < 0.66 and f.port is None and not f.queue and not f.derelict:
        f.jury_rig(rng.choice(('ENG', 'RDR', 'HUL')), g)
    elif r < 0.72 and not f.derelict:
        wrecks = g.wrecks()
        if wrecks and not f.queue:
            f.enqueue_tow(rng.choice(wrecks), g)
    elif r < 0.80:
        if f.agent < 3 and rng.random() < 0.3:
            f.agent += 1
        codes = [p.code for p in g.ports]
        f.circuit = dict(ports=rng.sample(codes, rng.randint(2, 4)),
                         paused=rng.random() < 0.3)
    elif r < 0.84:
        f.circuit = None
    elif r < 0.88:
        dark = [n for n in routes.NODES
                if n not in routes.PORTS and n not in g.buoys]
        if dark:
            g.buy_buoy(rng.choice(dark))
    elif r < 0.92 and f.derelict and f.port and not f.queue:
        f.enqueue_repair('HUL', g)


def run(seed, ticks):
    g = sim.Game(seed=seed)
    rng = random.Random(seed * 7 + 1)
    for t in range(ticks):
        for _ in range(rng.randint(0, 3)):
            act(g, rng)
        g.step()
        invariants(g, t, seed)
        if t % 400 == 200:
            g.save(SAVE)
            g = sim.load(SAVE)
            invariants(g, t, seed)
    return g


if __name__ == '__main__':
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    for seed in range(seeds):
        g = run(seed, ticks)
        print(f"seed {seed:2d}: T{g.tick_no} credits {int(g.credits):>9,} ok")
    if os.path.exists(SAVE):
        os.remove(SAVE)
    print("FUZZ OK")
