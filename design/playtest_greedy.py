"""Headless greedy playtest of prototype2: a competent-but-simple player.

Strategy per idle docked ship:
  - group apron offers by destination, pick the destination whose bundle
    (items that fit the hold, best pay first) maximizes pay - fuel,
    counting only items whose window survives the trip
  - load it, commit the most stable route (tie -> cheaper fuel)
  - if nothing profitable, sail empty to the port with the best such
    bundle available for pickup... or just wait for refresh

Tracks: credits over time, damage events, misses, interrupts per run.

This is the baseline the design gates in undecided-sound.html are written
against: a player who ignores the observation economy entirely -- never
observes, pings, reads an instrument, or lights a buoy. Today it wins
anyway (~$80k mean over 5 seeds, 400 ticks). Under the campaign design it
should go broke.

    python design/playtest_greedy.py
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'prototype2'))
import sim, routes, world

def best_bundle(game, ship, port):
    """(net, dest, items, option) best over destinations from this port."""
    best = None
    for dest in game.ports:
        if dest is port:
            continue
        items = sorted([c for c in port.cargo if c.dest is dest and not c.void],
                       key=lambda c: -c.payment)[:ship.hold_cap()]
        if not items:
            continue
        opts = routes.options(port.code, dest.code, game.water_for(ship))
        if not opts:
            continue
        # most stable, then cheapest fuel
        opt = sorted(opts, key=lambda o: (-o.stability(game.water_for(ship)), o.nm))[0]
        ticks = opt.ticks(ship.speed_pt())
        keep = [c for c in items if c.window > ticks + 1]
        if not keep:
            continue
        bonus = 1.0 + 0.05 * (len(keep) - 1)
        pay = int(sum(c.payment for c in keep) * bonus)
        fuel = opt.nm * ship.eff()
        net = pay - fuel
        if best is None or net > best[0]:
            best = (net, dest, keep, opt)
    return best

def step_runs(game, stats, max_ticks):
    """RETURN-style run: tick until an interrupt fires."""
    run = 0
    while game.tick_no < max_ticks:
        out = game.step()
        run += 1
        stats['ticks'] += 1
        for kind, msg in out:
            stats['interrupts'][kind] = stats['interrupts'].get(kind, 0) + 1
        if out:
            stats['runs'].append(run)
            return
    stats['runs'].append(run)

def main(seed):
    random.seed(seed)
    game = sim.Game(seed=seed)
    stats = dict(ticks=0, interrupts={}, runs=[], legs=0, empty=0,
                 credits=[(0, game.credits)])
    MAX = 400
    while game.tick_no < MAX:
        acted = False
        for ship in game.ships:
            if ship.derelict or ship.queue or ship.port is None:
                continue
            b = best_bundle(game, ship, ship.port)
            if b and b[0] > 0:
                net, dest, items, opt = b
                for c in items:
                    ship.port.cargo.remove(c)
                    ship.cargo.append(c)
                ship.enqueue_leg(opt, dest.code, game)
                stats['legs'] += 1
                acted = True
            else:
                stats['empty'] += 1
        # repair when badly damaged and docked
        for ship in game.ships:
            if ship.port and not ship.queue and not ship.derelict:
                for comp in ('ENG', 'RDR', 'HUL'):
                    if ship.components[comp] < 50 and game.credits > 2000:
                        ship.enqueue_repair(comp, game)
                        break
        step_runs(game, stats, MAX)
        stats['credits'].append((game.tick_no, game.credits))

    print(f"seed {seed}: tick {game.tick_no}  credits ${game.credits:,}")
    print(f"  legs committed: {stats['legs']}, no-profitable-bundle idles: {stats['empty']}")
    print(f"  interrupts: {stats['interrupts']}")
    runs = stats['runs']
    print(f"  runs: n={len(runs)} avg={sum(runs)/max(1,len(runs)):.1f} ticks between stops")
    lo = min(c for _, c in stats['credits']); hi = max(c for _, c in stats['credits'])
    print(f"  credits min ${lo:,} max ${hi:,}")
    for f in game.ships:
        print(f"  {f.name}: {f.components} derelict={f.derelict} pos={[round(p,1) for p in f.pos]}")
    return game.credits

if __name__ == '__main__':
    total = []
    for seed in (1, 2, 3, 4, 5):
        total.append(main(seed))
    print(f"\nmean final credits over {len(total)} seeds: ${sum(total)/len(total):,.0f} (start $10,000, 400 ticks)")
