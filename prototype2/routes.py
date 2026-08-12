"""The route network. Nodes are ports, buoy stations, and open-water
junctions; edges are the lanes between them. A leg is committed as a
polyline of world positions; stability is a property of the water the
path actually crosses, sampled from the game's coverage model.

Everything here is pure geometry -- no pygame, no game state except the
stability function callers pass in.
"""
import heapq
import math

import world

# node id -> position. Ports share their port codes.
NODES = {
    'MER': (20, 18), 'EDM': (40, 21), 'KNG': (72, 14), 'SHY': (94, 22),
    'B1': (28, 16), 'B2': (34, 14),                      # Mercer lane
    'B3a': (45, 18),                                     # Edmonds approach
    'B3': (50, 15), 'B4': (58, 13), 'B5': (65, 12),      # northern lane
    'J6': (80, 18), 'J7': (88, 20),                      # yard junctions
    'S1': (46, 24), 'S2': (56, 26), 'S3': (64, 25),      # southern basin
}
PORTS = ('MER', 'EDM', 'KNG', 'SHY')

EDGES = [('MER', 'B1'), ('B1', 'B2'), ('B2', 'EDM'),
         ('EDM', 'B3a'), ('B3a', 'B3'), ('B3', 'B4'), ('B4', 'B5'), ('B5', 'KNG'),
         ('KNG', 'J6'), ('J6', 'J7'), ('J7', 'SHY'),
         ('EDM', 'S1'), ('S1', 'S2'), ('S2', 'S3'), ('S3', 'KNG')]

_ADJ = {}
for a, b in EDGES:
    _ADJ.setdefault(a, []).append(b)
    _ADJ.setdefault(b, []).append(a)


def water_clear(a, b):
    """True if the straight line a->b stays off land."""
    d = world.dist(a, b)
    n = max(2, int(d * 2))
    for i in range(n + 1):
        t = i / n
        if world.land(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t):
            return False
    return True


def path_len(path):
    return sum(world.dist(path[i], path[i + 1]) for i in range(len(path) - 1))


def point_along(path, nm):
    """Position nm nautical miles along a polyline (clamped to its ends)."""
    for i in range(len(path) - 1):
        seg = world.dist(path[i], path[i + 1])
        if nm <= seg or i == len(path) - 2:
            t = min(1.0, nm / seg) if seg else 1.0
            return (path[i][0] + (path[i + 1][0] - path[i][0]) * t,
                    path[i][1] + (path[i + 1][1] - path[i][1]) * t)
        nm -= seg
    return path[-1]


def sample(path, step=1.5):
    """Points every ~step NM along a polyline (both endpoints included)."""
    total = path_len(path)
    n = max(1, int(total / step))
    return [point_along(path, total * i / n) for i in range(n + 1)]


def _dijkstra(src, dst, cost):
    """cost(a, b) -> edge weight. Returns node id list or None."""
    dist, prev = {src: 0.0}, {}
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == dst:
            break
        if d > dist.get(u, 9e9):
            continue
        for v in _ADJ.get(u, ()):
            nd = d + cost(u, v)
            if nd < dist.get(v, 9e9):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    if dst not in dist:
        return None
    out, u = [dst], dst
    while u != src:
        u = prev[u]
        out.append(u)
    return out[::-1]


def nearest_node(pos):
    return min(NODES, key=lambda n: world.dist(pos, NODES[n]))


class Option:
    """One committed-cost route offer: exact NM, exact path, rated water."""

    def __init__(self, name, path):
        self.name = name
        self.path = [tuple(p) for p in path]
        self.nm = path_len(self.path)

    def ticks(self, speed_pt):
        return max(1, math.ceil(self.nm / speed_pt))

    def fuel(self, eff):
        return int(self.nm * eff)

    def stability(self, stab_fn):
        """Worst water on the path decides the rating -- min over samples."""
        return min(stab_fn(x, y) for x, y in sample(self.path))


def options(start, dest_id, stab_fn):
    """Route offers from `start` (node id, or world pos) to a destination
    node. Returns [Option], best-known lane first; may be empty only if the
    start is boxed in, which the geography does not allow."""
    dpos = NODES[dest_id]
    out = []

    if isinstance(start, str):
        spos = NODES[start]
        lane = _dijkstra(start, dest_id,
                         lambda a, b: world.dist(NODES[a], NODES[b]))
        if lane and len(lane) > 2:
            out.append(Option('LANE', [NODES[n] for n in lane]))
    else:
        # at sea: join the network at the nearest node, then ride the lanes
        spos = tuple(start)
        join = nearest_node(spos)
        if join != dest_id and water_clear(spos, NODES[join]):
            lane = _dijkstra(join, dest_id,
                             lambda a, b: world.dist(NODES[a], NODES[b]))
            if lane:
                out.append(Option('LANE', [spos] + [NODES[n] for n in lane]))

    if water_clear(spos, dpos):
        out.append(Option('DIRECT', [spos, dpos]))

    # a lane that is really just the direct line is noise, not two options.
    # Keep the LANE form: it snaps to stations, so lighting buoys helps it.
    if len(out) == 2 and abs(out[0].nm - out[1].nm) < 0.5:
        out = [out[0]]
    out.sort(key=lambda o: -o.stability(stab_fn))
    return out
