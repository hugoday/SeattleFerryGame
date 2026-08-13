"""Headless behavior checks for the tick world. No pygame required.

Run:  python checks.py
Each scenario asserts the mechanics the milestone promises. Failures raise.
"""
import json
import os
import sys

import routes
import sim
import world


def fresh(seed):
    return sim.Game(seed=seed)


def send(g, f, kind, src, dst):
    """Put f at src and commit the named option toward dst."""
    if f.port is not None:
        f.port.ferries.remove(f)
        f.port = None
    f.pos = list(routes.NODES[src])
    opts = routes.options(src, dst, g.water_for(f))
    o = next(x for x in opts if x.name == kind)
    f.queue.append(dict(kind='leg', path=[list(p) for p in o.path],
                        nm=o.nm, done=0.0, dest=dst))
    return o


def sail(g, f, limit=99):
    t0 = g.tick_no
    while f.port is None and not f.derelict and g.tick_no - t0 < limit:
        g.step()


def dmg(f):
    return 300 - sum(f.components.values())


# 1. lane through decided water arrives clean; the basin costs hulls -------
def check_water():
    lane_d, basin_d = [], []
    for s in range(25):
        g = fresh(s); f = g.ships[0]
        send(g, f, 'LANE', 'MER', 'KNG')
        sail(g, f)
        lane_d.append(dmg(f))
        g2 = fresh(1000 + s); f2 = g2.ships[0]
        if f2.port:
            f2.port.ferries.remove(f2); f2.port = None
        f2.pos = [46.0, 24.0]
        path = [[46, 24], [56, 26], [64, 25], [72, 14]]
        f2.queue.append(dict(kind='leg', path=path,
                             nm=routes.path_len(path), done=0.0, dest='KNG'))
        sail(g2, f2)
        basin_d.append(dmg(f2))
    assert max(lane_d) == 0, f"buoyed lane should be safe, saw {max(lane_d)}"
    assert sum(basin_d) / len(basin_d) > 4, \
        f"basin should attrit, avg {sum(basin_d) / len(basin_d):.1f}"
    print(f"  water: lane max dmg 0, basin avg {sum(basin_d)/len(basin_d):.1f} OK")


# 2. observed flag protects; striking it exposes ---------------------------
def check_flag():
    hits = 0
    for s in range(25):
        g = fresh(s); f = g.ships[0]
        if f.port:
            f.port.ferries.remove(f); f.port = None
        f.pos = [46.0, 24.0]
        path = [[46, 24], [56, 26], [64, 25], [72, 14]]
        f.queue.append(dict(kind='leg', path=path,
                            nm=routes.path_len(path), done=0.0, dest='KNG'))
        g.observed = f
        sail(g, f)
        hits += dmg(f)
    # dropouts (4%/tick) allow rare hits; the flag must stop nearly all
    assert hits <= 24, f"observed basin runs took {hits} dmg total"
    print(f"  flag: 25 observed basin crossings, {hits} total dmg OK")


# 3. hull zero -> derelict -> tow -> repair -> sails again ------------------
def check_derelict_tow():
    g = fresh(3)
    f, r = g.ships[0], g.ships[1]
    if f.port:
        f.port.ferries.remove(f); f.port = None
    f.pos = [56.0, 26.0]
    f.components['HUL'] = 4
    out = []
    while not f.derelict and g.tick_no < 300:
        f.queue = [dict(kind='leg', path=[[56, 26], [46, 24], [56, 26]],
                        nm=20.4, done=0.0, dest=None)] if not f.queue else f.queue
        out = g.step()
    assert f.derelict, "hull at 4 in the basin should go derelict"
    assert not f.queue, "derelict queue must clear"
    r.enqueue_tow(f, g)
    for _ in range(200):
        g.step()
        if r.port is not None and f.port is not None:
            break
    assert f.port is g.shipyard(), "wreck should be towed into the yard"
    f.enqueue_repair('HUL', g)
    for _ in range(20):
        g.step()
    assert not f.derelict and f.components['HUL'] == 100, "repair must revive"
    print("  derelict: wrecked, towed, rebuilt OK")


# 4. abandon voids cargo and debits standing by progress -------------------
def check_abandon():
    g = fresh(4)
    f = g.ships[0]
    p = g.ports[0]
    c = sim.Contract(p, g.ports[2], 'Test crates', 1000, 50)
    f.cargo.append(c)
    send(g, f, 'LANE', 'MER', 'KNG')
    for _ in range(6):
        g.step()
    s0 = p.standing
    g.abandon(f)
    assert c.void, "abandoned contract must void"
    assert p.standing < s0, "abandonment must cost standing at the origin"
    mid_cost = s0 - p.standing
    assert mid_cost > 6, f"mid-route abandon should cost more than base, got {mid_cost}"
    print(f"  abandon: mid-route cost {mid_cost} standing OK")


# 5. a window that closes in custody is a miss -----------------------------
def check_window():
    g = fresh(5)
    f = g.ships[0]
    p = g.ports[0]
    c = sim.Contract(p, g.ports[1], 'Late crates', 2000, 3)
    f.cargo.append(c)
    s0, cr0 = p.standing, g.credits
    for _ in range(4):
        g.step()
    assert c.void, "expired contract in custody must void"
    assert p.standing == s0 - sim.STAND_MISS, "miss must debit standing"
    assert g.credits < cr0, "miss must carry a financial penalty"
    print("  window: miss voids, debits standing and credits OK")


# 6. delivery inside the window pays and lifts standing --------------------
def check_delivery():
    g = fresh(6)
    f = g.ships[0]
    p = g.ports[0]
    f.cargo.append(sim.Contract(p, g.ports[2], 'Prompt crates', 1500, 60))
    s0 = p.standing
    cr0 = g.credits
    send(g, f, 'LANE', 'MER', 'KNG')
    sail(g, f)
    assert f.port is g.ports[2] and not f.cargo, "delivery should complete"
    assert p.standing == s0 + sim.STAND_DELIVER, "delivery must lift standing"
    print("  delivery: paid, standing lifted OK")


# 7. buying a buoy lights the yard corridor --------------------------------
def check_buoys():
    g = fresh(7)
    f = g.ships[0]
    w = g.water_for(f)
    before = next(o for o in routes.options('KNG', 'SHY', w)).stability(w)
    assert g.buy_buoy('J6') and g.buy_buoy('J7')
    after = next(o for o in routes.options('KNG', 'SHY', w)).stability(w)
    assert after > before, f"lit corridor must rate higher ({before}->{after})"
    print(f"  buoys: KNG-SHY corridor {before}/4 -> {after}/4 OK")


# 8. emissions: pings echo, decay, and bait the anomaly --------------------
def check_noise():
    g = fresh(9)
    f = g.ships[0]
    g.ping(f)
    assert f.noise >= sim.NOISE_PING, "ping must raise the ledger"
    n0 = f.noise
    g.step()
    assert f.noise < n0, "noise must decay per tick"
    # a loud hull in the basin pulls the anomaly toward it
    pulled, ambient = [], []
    for s in range(20):
        for loud in (True, False):
            g = fresh(200 + s)
            f = g.ships[0]
            if f.port:
                f.port.ferries.remove(f); f.port = None
            f.pos = [56.0, 28.0]
            g.tick_no = sim.ANOMALY_WAKES     # wake it immediately
            for _ in range(12):
                if loud:
                    f.noise = 100             # held loud
                g.step()
            d = world.dist(f.pos, g.anomaly.pos)
            (pulled if loud else ambient).append(d)
    pa, aa = sum(pulled) / len(pulled), sum(ambient) / len(ambient)
    assert pa < aa, f"noise should bait the anomaly ({pa:.1f} !< {aa:.1f})"
    print(f"  noise: ping echoes, decays; anomaly closes {aa:.1f}->{pa:.1f} NM OK")


# 9. the anomaly up close corrupts hulls and deresolves manifests ----------
def check_anomaly_touch():
    hul_hit = cargo_hit = 0
    for s in range(10):
        g = fresh(300 + s)
        f = g.ships[0]
        f.port.ferries.remove(f); f.port = None
        f.cargo.append(sim.Contract(g.ports[0], g.ports[2], 'Bait', 1000, 99))
        g.tick_no = sim.ANOMALY_WAKES
        for _ in range(6):
            f.pos = list(g.anomaly.pos)   # ride the contact
            g.step()
        hul_hit += 100 - f.components['HUL']
        cargo_hit += 1 if f.cargo and f.cargo[0].void else 0
    assert hul_hit > 100, f"contact should corrupt hulls, total {hul_hit}"
    assert cargo_hit >= 5, f"contact should deresolve cargo, {cargo_hit}/10"
    print(f"  anomaly: avg {hul_hit/10:.0f} hull dmg, {cargo_hit}/10 holds "
          f"deresolved OK")


# 10. interpret: the honest instrument is right, the other lies -------------
def check_interpret():
    import math
    honest_err, lying_err = [], []
    for s in range(20):
        g = fresh(400 + s)
        f = g.ships[0]
        f.port.ferries.remove(f); f.port = None
        f.pos = [50.0, 22.0]
        g.tick_no = sim.ANOMALY_WAKES
        g.step()
        c = g.anomaly_claims(f)
        if not c:
            continue
        true = tuple(g.anomaly.pos)
        sonar = (f.pos[0] + math.cos(c['sonar_brg']) * c['rng'],
                 f.pos[1] + math.sin(c['sonar_brg']) * c['rng'])
        r_err, s_err = world.dist(c['radar'], true), world.dist(sonar, true)
        if g.anomaly.honest == 'radar':
            honest_err.append(r_err); lying_err.append(s_err)
        else:
            honest_err.append(s_err); lying_err.append(r_err)
    assert max(honest_err) < 0.6, f"honest read must be true, {max(honest_err):.2f}"
    assert min(lying_err) > 1.0, f"lying read must be off, {min(lying_err):.2f}"
    # a committed read drives the board's working fix
    g = fresh(431)
    f = g.ships[0]
    f.port.ferries.remove(f); f.port = None
    f.pos = [50.0, 24.5]
    g.tick_no = sim.ANOMALY_WAKES
    g.step()
    g.anomaly.pos = [56.0, 30.0]          # push it outside all coverage
    if g.stability(*g.anomaly.pos) < 2 and g.anomaly_claims(f):
        g.set_read('radar')
        rep = g.anomaly_report()
        assert rep and rep[3] == 'FIX/RADAR', f"fix should follow the read: {rep}"
    print(f"  interpret: honest err<{max(honest_err):.2f}, lying "
          f"err>{min(lying_err):.2f}, fix follows the read OK")


# 11. helm: heading and throttle only, and the shore refuses her ------------
def check_helm():
    g = fresh(11)
    f = g.ships[0]
    f.set_helm(0, 2, g)                   # due east at CRUISE
    p0 = tuple(f.pos)
    g.step()
    assert world.dist(p0, f.pos) > 3.0, "cruise helm must move her"
    f.queue[0]['thr'] = 3
    n_cruise = f.noise
    g.step()
    assert f.noise > n_cruise, "flank must be louder than cruise"
    # aim her at Mercer Island and let the helm refuse
    f.pos = [20.0, 15.0]
    f.queue[0].update(hdg=90, thr=3)      # due south into the island
    for _ in range(6):
        g.step()
        if f.queue[0]['thr'] == 0:
            break
    assert f.queue[0]['thr'] == 0, "the helm must stop at breakers"
    print("  helm: moves, flank is loud, breakers stop her OK")


# 12. manage: powered-down systems ride it out; the hull never can ----------
def check_manage():
    g = fresh(12)
    f = g.ships[0]
    f.port.ferries.remove(f); f.port = None
    f.pos = [50.0, 27.0]
    f.power['ENG'] = f.power['RDR'] = False
    for _ in range(40):
        g.step()
        if f.derelict:
            break
    assert f.components['ENG'] == 100 and f.components['RDR'] == 100, \
        "shielded components must not take drift damage"
    assert f.components['HUL'] < 100, "the hull is always in the water"
    print(f"  manage: dark boat kept ENG/RDR at 100, HUL "
          f"{f.components['HUL']} OK")


# 13. agents: T2 works the circuit; T1 stops dead; T3 finds sea room --------
def check_agents():
    g = fresh(13)
    f = g.ships[0]
    f.agent = 2
    f.circuit = dict(ports=['MER', 'EDM', 'KNG'], paused=False)
    arrivals = loads = 0
    for _ in range(100):
        for k, m in g.step():
            arrivals += 1 if k == 'idle' else 0
        loads = max(loads, len(f.cargo))
    assert arrivals >= 6, f"T2 should keep the circuit turning, {arrivals}"
    assert loads > 0, "T2 must load cargo without being told"
    g = fresh(14)
    f = g.ships[0]
    g.tick_no = sim.ANOMALY_WAKES
    g.step()
    g.anomaly.pos = [56.0, 17.5]          # on the EDM-KNG waterline
    g.anomaly_seen = (56.0, 17.5, g.tick_no)
    f.agent = 1
    f.circuit = dict(ports=['EDM', 'KNG'], paused=False)
    f.port.ferries.remove(f)
    f.port = g.ports[1]; f.pos = list(g.ports[1].pos)
    g.ports[1].ferries.append(f)
    for _ in range(3):
        g.anomaly_seen = (56.0, 17.5, g.tick_no)
        g.step()
    assert f.circuit['paused'], "T1 must stop dead on a contact near the route"
    f.agent = 3
    f.circuit['paused'] = False
    sailed = False
    for _ in range(4):
        g.anomaly.pos = [56.0, 17.5]
        g.anomaly_seen = (56.0, 17.5, g.tick_no)
        g.step()
        sailed = sailed or bool(f.queue)
    assert sailed and not f.circuit['paused'], "T3 must divert, not freeze"
    print(f"  agents: T2 ran {arrivals} arrivals + loaded {loads}, "
          f"T1 froze, T3 diverted OK")


# 14. save -> load -> save is byte-identical mid-everything -----------------
def check_save():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_check_save')
    a, b = out + '_a.json', out + '_b.json'
    g = fresh(8)
    f = g.ships[0]
    p0 = g.ports[0]
    for c in list(p0.cargo[:2]):
        p0.cargo.remove(c); f.cargo.append(c)
    send(g, f, 'LANE', 'MER', 'KNG')
    g.set_observed(f)
    g.ships[1].enqueue_repair('RDR', g) if g.ships[1].repair_quote('RDR') \
        else None
    g.buy_buoy('J6')
    g.set_read('sonar')
    f.power['RDR'] = False
    f.agent = 2
    f.circuit = dict(ports=['MER', 'KNG'], paused=True)
    for _ in range(4):
        g.step()
    g.save(a)
    g2 = sim.load(a)
    g.log("state restored from disk")          # mirror load()'s event
    g.events[-1] = g2.events[-1]
    g.save(a)
    g2.save(b)
    ja, jb = open(a).read(), open(b).read()
    assert ja == jb, "save -> load -> save must be byte-identical"
    os.remove(a); os.remove(b)
    print("  save: round-trip byte-identical OK")


if __name__ == '__main__':
    print("prototype2 checks:")
    check_water()
    check_flag()
    check_derelict_tow()
    check_abandon()
    check_window()
    check_delivery()
    check_buoys()
    check_noise()
    check_anomaly_touch()
    check_interpret()
    check_helm()
    check_manage()
    check_agents()
    check_save()
    print("ALL OK")
