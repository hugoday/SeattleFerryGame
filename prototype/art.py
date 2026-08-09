"""Hull art: plan view and outboard profile, quantised to CP437 halves.

Material fields are sampled per cell; each cell resolves to at most two
colours expressed as (glyph, fg, bg) -- honest text mode. Results are cached
per state, so the field maths runs only when the ship actually changes.
"""

SS = 6                                # sub-samples per cell axis

# material -> palette key (None = transparent)
MATCOL = {0: None, 1: 'c', 2: 'S', 3: 'g', 4: 'd', 5: 'a',
          6: 'D', 7: 'C', 8: 'D', 9: 'd', 10: 'D', 11: 'a', 12: 'R'}

_HALVES = [('█', 1, 1, 1, 1), ('▀', 1, 1, 0, 0), ('▄', 0, 0, 1, 1),
           ('▌', 1, 0, 1, 0), ('▐', 0, 1, 0, 1)]

_cache = {}


def _quantise(mats):
    """SS*SS material ids -> (glyph, fg_key, bg_key) or None."""
    counts = {}
    for m in mats:
        counts[m] = counts.get(m, 0) + 1
    order = sorted(counts, key=lambda k: -counts[k])
    a = order[0]
    if len(order) == 1:
        col = MATCOL[a]
        return ('█', col, None) if col else None
    b = order[1]
    # quadrant occupancy of material a
    half = SS // 2
    q = [0, 0, 0, 0]
    tot = [0, 0, 0, 0]
    for j in range(SS):
        for i in range(SS):
            k = (0 if j < half else 2) + (0 if i < half else 1)
            tot[k] += 1
            if mats[j * SS + i] == a:
                q[k] += 1
    occ = [1 if q[k] * 2 >= tot[k] else 0 for k in range(4)]
    best, bscore = '█', -1
    for g, tl, tr, bl, br in _HALVES:
        score = sum(1 for got, want in zip(occ, (tl, tr, bl, br)) if got == want)
        if score > bscore:
            best, bscore = g, score
    ca, cb = MATCOL[a], MATCOL[b]
    if ca is None:                     # a transparent: draw b in the inverse
        inv = {'█': ' ', '▀': '▄', '▄': '▀', '▌': '▐', '▐': '▌'}[best]
        return (inv, cb, None) if inv != ' ' and cb else (
            ('█', cb, None) if cb else None)
    return best, ca, cb


def _render(fn, cols, rows):
    cells = []
    for cy in range(rows):
        for cx in range(cols):
            mats = [fn((cx + (i + 0.5) / SS) / cols,
                       (cy + (j + 0.5) / SS) / rows)
                    for j in range(SS) for i in range(SS)]
            if not any(mats):
                continue
            out = _quantise(mats)
            if out:
                cells.append((cx, cy, out[0], out[1], out[2]))
    return cells


def draw_field(scr, x, y, cols, rows, key, fn):
    cells = _cache.get(key)
    if cells is None:
        cells = _render(fn, cols, rows)
        _cache[key] = cells
    for cx, cy, ch, fg, bg in cells:
        scr.put(x + cx, y + cy, ch, fg, bg)


# ---------------------------------------------------------------- plan view
def plan_field(crates, cap):
    rows = max(2, (cap + 1) // 2)

    def fn(u, v):
        x = (u - 0.5) * 2.0                       # -1..1 across beam
        au = abs(x)
        if v < 0.02 or v > 0.985:
            return 0
        hb = 1.0
        if v < 0.22:
            hb = 0.26 + 0.74 * (v / 0.22) ** 0.6
        elif v > 0.86:
            hb = 1.0 - 0.18 * ((v - 0.86) / 0.14) ** 1.5
        if au > hb:
            return 0
        if au > hb - 0.16:
            return 1                              # shell
        if 0.585 < v < 0.615 and au < 0.14:
            return 5                              # sensor mast
        if 0.63 < v < 0.78 and au < 0.52:         # bridge: compute racks
            cu, cv = au / 0.52, (v - 0.63) / 0.15
            return 7 if (cu * 2 % 1 > 0.25 and cv * 2 % 1 > 0.28) else 4
        if 0.13 < v < 0.56 and au < 0.72:         # cargo bays
            # Bays run across the beam (2 abreast) and fore-aft. An odd
            # capacity puts a single centred bay in the aftmost row, so the
            # drawing always shows exactly `cap` bays -- no phantoms, and no
            # mirroring about the centreline.
            cv = (v - 0.13) / 0.43
            row = min(int(cv * rows), rows - 1)
            fv = cv * rows - row
            base = row * 2
            in_row = min(2, cap - base)
            if in_row <= 0:
                return 6
            t = (x + 0.72) / 1.44                 # 0..1 across the bay area
            if in_row == 1:
                if not 0.25 <= t < 0.75:
                    return 2
                col, fu = 0, (t - 0.25) * 2
            else:
                col = 0 if t < 0.5 else 1
                fu = t * 2 - col
            slot = base + col
            if 0.12 < fu < 0.88 and 0.14 < fv < 0.86:
                return 3 if slot < crates else 2      # loaded / empty bay
            return 6                                  # coaming between bays
        if v > 0.84 and au < 0.40:
            return 5                              # machinery
        return 6

    return fn


def draw_plan(scr, x, y, ferry, cols=9, rows=17):
    key = ('plan', ferry.cls, len(ferry.cargo), ferry.hold_cap(), cols, rows)
    draw_field(scr, x, y, cols, rows, key, plan_field(len(ferry.cargo),
                                                      ferry.hold_cap()))


# ---------------------------------------------------------------- profile
def profile_field(crates, cap, load, sea=True):
    DECK, KEEL = 0.44, 0.84
    wl = 0.64 - 0.075 * (1.0 - load)

    def deck_y(x):
        return DECK - 0.075 * (1 - x) ** 2.4 - 0.02 * x ** 3

    def stem_x(y):
        d0 = deck_y(0.1)
        t = min(1.0, max(0.0, (y - d0) / (KEEL - d0)))
        return 0.02 + 0.11 * t ** 1.25

    def fn(x, y):
        dy = deck_y(x)
        ky = KEEL - (0.10 * ((x - 0.90) / 0.10) ** 1.7 if x > 0.90 else 0)
        inhull = stem_x(y) <= x <= 0.965 and dy <= y <= ky
        if not inhull and y < ky:
            if 0.60 < x < 0.625 and 0.10 < y < dy:
                return 5                          # mast
            if 0.64 < x < 0.80 and dy - 0.20 < y < dy:
                cu, cv = (x - 0.64) / 0.16, (y - dy + 0.20) / 0.20
                return 7 if (cu * 3 % 1 > 0.22 and cv * 2 % 1 > 0.25) else 4
            if 0.815 < x < 0.86 and dy - 0.26 < y < dy:
                return 5                          # stack
            if 0.08 < x < 0.585 and dy - 0.13 < y < dy:
                cu = (x - 0.08) / 0.505           # deck crates
                col = min(int(cu * cap), cap - 1)
                fu = cu * cap - col
                return 3 if (col < crates and 0.08 < fu < 0.92) else 0
        if not inhull:
            if sea and y > wl:
                return 12 if y < wl + 0.02 else 8
            return 0
        if sea and abs(y - wl) < 0.018:
            return 11                             # boot top
        sub = sea and y > wl
        if (y < dy + 0.028 or y > ky - 0.028
                or x < stem_x(y) + 0.028 or x > 0.94):
            return 9 if sub else 1
        return 10 if sub else 6

    return fn


def draw_profile(scr, x, y, ferry, cols=46, rows=9, sea=True):
    load = len(ferry.cargo) / max(1, ferry.hold_cap())
    key = ('prof', ferry.cls, len(ferry.cargo), ferry.hold_cap(), cols, rows, sea)
    draw_field(scr, x, y, cols, rows, key,
               profile_field(len(ferry.cargo), ferry.hold_cap(), load, sea))
