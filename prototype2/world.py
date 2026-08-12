"""Geography in nautical miles. Land is a field rasterised once at boot,
then sampled into cells at any range scale with CP437 half-blocks."""
import math

W, H = 112.0, 36.0
RES = 4                      # raster samples per NM

# (cx, cy, rx, ry, weight)
BLOBS = [
    (30, -13, 46, 17, 1.30), (86, -11, 40, 15, 1.30),
    (26, 49, 42, 17, 1.30), (88, 50, 44, 18, 1.30),
    (18, 13, 9, 4, 1.00),        # Mercer
    (38, 25, 8, 4, 1.00),        # Edmonds peninsula
    (72, 9, 10, 4, 1.00),        # Kingston
    (95, 25, 9, 4, 1.00),        # Shipyard island
    (55, 8, 6, 3, 0.90), (60, 30, 5, 2, 0.90), (84, 16, 4, 2, 0.85),
]
# Carved water: port approaches, the northern buoy lane, the junctions out
# to the yard, and the southern basin the anomaly calls home.
CHANNELS = [(20, 18), (28, 16), (34, 14), (40, 21), (50, 15), (58, 13),
            (65, 12), (72, 14), (80, 18), (88, 20), (94, 22),
            (46, 24), (56, 26), (64, 25)]


def _h(ix, iy, s=0):
    n = (ix * 374761393 + iy * 668265263 + s * 2147483647) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def _noise(x, y, s=0):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a, b = _h(ix, iy, s), _h(ix + 1, iy, s)
    c, d = _h(ix, iy + 1, s), _h(ix + 1, iy + 1, s)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _fbm(x, y):
    return (_noise(x, y) * 0.55 + _noise(x * 2.1, y * 2.1, 1) * 0.28
            + _noise(x * 4.3, y * 4.3, 2) * 0.17)


def _land_slow(x, y):
    v = 0.0
    for cx, cy, rx, ry, w in BLOBS:
        d = math.hypot((x - cx) / rx, (y - cy) / ry)
        if d < 1.6:
            v += w * max(0.0, 1.0 - d)
    if v <= 0.0:
        return False
    v += (_fbm(x * 0.09, y * 0.09) - 0.5) * 0.85
    if v <= 0.30:
        return False
    for cx, cy in CHANNELS:
        if math.hypot(x - cx, y - cy) < 3.0:
            return False
    return True


_GW, _GH = int(W * RES) + 2, int(H * RES) + 2
_grid = None


def build():
    global _grid
    _grid = bytearray(_GW * _GH)
    for j in range(_GH):
        for i in range(_GW):
            if _land_slow(i / RES, j / RES):
                _grid[j * _GW + i] = 1


def land(x, y):
    if _grid is None:
        build()
    if x < 0 or y < 0 or x >= W or y >= H:
        return False
    return _grid[int(y * RES) * _GW + int(x * RES)] == 1


_QUAD = {(1, 1, 1, 1): '█', (1, 1, 0, 0): '▀', (0, 0, 1, 1): '▄',
         (1, 0, 1, 0): '▌', (0, 1, 0, 1): '▐'}


def cell_glyph(x0, y0, sx, sy):
    """Sample one cell's footprint -> (glyph, full?) or None for open water."""
    q = tuple(1 if land(x0 + sx * ox, y0 + sy * oy) else 0
              for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)))
    n = sum(q)
    if n == 0:
        return None
    if n == 4:
        return '█', True
    g = _QUAD.get(q)
    if g:
        return g, False
    return ('█', False) if n >= 3 else ('▒', False)


def near_land(x, y, r):
    for a in range(0, 360, 45):
        t = math.radians(a)
        if land(x + math.cos(t) * r, y + math.sin(t) * r):
            return True
    return False


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])
