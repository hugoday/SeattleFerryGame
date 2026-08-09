"""Views. Each has draw(scr, game) and key(k, game) -> next view name.

The sim ticks regardless of which view is up -- screens are windows onto a
world that does not wait for you.
"""
import math
import pygame as pg

import art
import world
from sim import PORT_UPG


def header(scr, game, left, mid=''):
    scr.text(1, 0, left, 'w')
    if mid:
        scr.text(len(left) + 3, 0, mid, 'c')
    money_fg = 'g' if game.credits >= 0 else 'a'
    scr.rtext(scr.cols - 14, 0, f"${int(game.credits):,}", money_fg)
    if game.credits < 0:
        scr.rtext(scr.cols - 26, 0, 'ARREARS', 'a')
    scr.rtext(scr.cols - 2, 0, game.clock(), '_')
    scr.hline(0, 1, scr.cols, '═', 'c')


def eventline(scr, game):
    if game.events:
        t, msg, fg = game.events[-1]
        scr.text(1, scr.rows - 1, f"T+{int(t):02d}:{int(t % 1 * 60):02d}  {msg}"[:scr.cols - 2], fg)


def bearing(a, b):
    return int(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) + 90) % 360


# ======================================================================= map
class MapView:
    SCALES = [1.06, 0.42, 0.18]

    def __init__(self):
        self.scale_i = 0
        self.cx, self.cy = 56.0, 18.0
        self.sel = 0                     # selected port index
        self._terrain = {}
        self._shade = None
        self._shade_t = -9.0
        self.y0, self.mh = 2, 0

    # ---- projection ------------------------------------------------------
    def sx(self):
        return self.SCALES[self.scale_i]

    def to_cell(self, scr, wx, wy):
        sx = self.sx(); sy = sx * (scr.ch / scr.cw)
        x0 = self.cx - sx * scr.cols / 2
        y0 = self.cy - sy * self.mh / 2
        return int(round((wx - x0) / sx)), int(round((wy - y0) / sy)) + self.y0

    def draw(self, scr, game):
        self.mh = scr.rows - 7
        sx = self.sx(); sy = sx * (scr.ch / scr.cw)
        x0 = self.cx - sx * scr.cols / 2
        y0 = self.cy - sy * self.mh / 2

        # ---- terrain (cached per viewport) -------------------------------
        tkey = (self.scale_i, round(x0, 2), round(y0, 2), scr.cols, self.mh)
        terr = self._terrain.get(tkey)
        if terr is None:
            terr = {}
            for cy in range(self.mh):
                for cx in range(scr.cols):
                    g = world.cell_glyph(x0 + cx * sx, y0 + cy * sy, sx, sy)
                    if g:
                        terr[(cx, cy)] = g
            self._terrain = {tkey: terr}
        for (cx, cy), (g, full) in terr.items():
            scr.put(cx, cy + self.y0, g, 'L' if full else 'l')

        # ---- uncertainty shading (recomputed on a slow cadence) ----------
        if game.t - self._shade_t > 0.05 or self._shade is None \
                or self._shade[0] != tkey:
            shade = {}
            for cy in range(self.mh):
                for cx in range(scr.cols):
                    if (cx, cy) in terr:
                        continue
                    wx, wy = x0 + (cx + 0.5) * sx, y0 + (cy + 0.5) * sy
                    d = game.uncertainty(wx, wy)
                    if d >= 1.0:
                        shade[(cx, cy)] = 0 if d < 1.3 else (1 if d < 1.7 else 2)
            self._shade = (tkey, shade)
            self._shade_t = game.t
        frame = int(game.t * 40)
        for (cx, cy), lvl in self._shade[1].items():
            if lvl == 0:
                g = '░'
            else:                        # unresolved water flickers
                r = (cx * 7 + cy * 13 + frame) % 11
                g = '▒▓░'[lvl - 1 + (1 if r == 0 else 0)] if lvl < 2 else \
                    ('▓' if r > 1 else '▒')
            scr.put(cx, cy + self.y0, g, 'd')

        # ---- routes ------------------------------------------------------
        for a, b, style in game.routes:
            self._route(scr, a, b, style, terr)

        # ---- assets ------------------------------------------------------
        for bx, by in game.buoys:
            px, py = self.to_cell(scr, bx, by)
            self._put_map(scr, px, py, '○', 'c')
        for i, p in enumerate(game.ports):
            px, py = self.to_cell(scr, *p.pos)
            sel = (i == self.sel)
            self._put_map(scr, px, py, '⌂', 'w' if sel else 'C')
            scr.text(px - 1, py + 1, p.code, 'w' if sel else 'C',
                     'S' if sel else None)
        for f in game.ferries:
            px, py = self.to_cell(scr, *f.pos)
            hx, hy = f.heading
            g = '►' if abs(hx) >= abs(hy) and hx >= 0 else \
                '◄' if abs(hx) >= abs(hy) else ('▼' if hy > 0 else '▲')
            self._put_map(scr, px, py, g, 'g')
            if self.scale_i > 0:
                scr.text(px + 2, py, f.name, 'g')
        if game.anomaly.alive:
            ax, ay = self.to_cell(scr, *game.anomaly.pos)
            self._put_map(scr, ax, ay, '?', 'm')
            if self.scale_i > 0:
                scr.text(ax + 2, ay, 'UNRESOLVED', 'm')

        # ---- chrome ------------------------------------------------------
        header(scr, game, 'PUGET SOUND OPERATING AREA')
        scr.text(30, 0, 'SCALE', 'c')
        scr.text(36, 0, ['STRATEGIC', 'REGIONAL', 'TACTICAL'][self.scale_i], 'w')
        scr.text(48, 0, f'1 cell = {self.sx():.2f} NM', 'c')
        scr.text(68, 0, 'ARRAY', 'c')
        scr.text(74, 0, '[NOMINAL]', 'g')

        fy = scr.rows - 5
        scr.hline(0, fy, scr.cols, '═', 'c')
        scr.text(1, fy + 1, 'CONTACTS', 'c')
        sp = game.ports[self.sel]
        # three reserved rows; the anomaly takes the last one when alive
        rows_avail = 3
        entries = []
        for f in game.ferries:
            st = f"brg {bearing(sp.pos, f.pos):03d}  " \
                 f"{world.dist(sp.pos, f.pos):5.1f} NM  " \
                 f"hold {len(f.cargo)}/{f.hold_cap()}  " + \
                 (f"ETA {int(f.eta_h() * 60):3d} min -> {f.dest.code}"
                  if f.moving else f"docked {f.port.code}")
            entries.append(('►', 'g', f.name, '_', st, '_'))
        if game.anomaly.alive:
            entries = entries[:rows_avail - 1]
            entries.append(('?', 'm', 'UNRESOLVED', 'm',
                            f"brg {bearing(sp.pos, game.anomaly.pos):03d}  "
                            f"{world.dist(sp.pos, game.anomaly.pos):5.1f} NM  "
                            f"radar/sonar disagree", 'a'))
        shown = entries[:rows_avail]
        for i, (g, gfg, name, nfg, st, sfg) in enumerate(shown):
            scr.text(12, fy + 1 + i, g, gfg)
            scr.text(14, fy + 1 + i, name, nfg)
            scr.text(26, fy + 1 + i, st, sfg)
        total = len(game.ferries) + (1 if game.anomaly.alive else 0)
        if total > len(shown):
            scr.text(1, fy + 2, f'+{total - len(shown)} more', 'd')
        for i, s in enumerate(('ARROWS PAN  -/+ RANGE', 'A/D SELECT PORT',
                               'SPACE OPEN  Q QUIT')):
            scr.rtext(scr.cols - 2, fy + 1 + i, s, 'c')
        eventline(scr, game)

    def _put_map(self, scr, x, y, ch, fg):
        if 0 <= x < scr.cols and self.y0 <= y < self.y0 + self.mh:
            scr.put(x, y, ch, fg)

    def _route(self, scr, a, b, style, terr):
        ax, ay = self.to_cell_raw(scr, *a)
        bx, by = self.to_cell_raw(scr, *b)
        dx = (bx > ax) - (bx < ax); dy = (by > ay) - (by < ay)
        x, y, guard = ax, ay, 0
        while (x, y) != (bx, by) and guard < 500:
            guard += 1
            if x != bx and y != by:
                x += dx; y += dy
                g = '\\' if dx == dy else '/'
            elif x != bx:
                x += dx; g = style if style != '─' else '─'
            else:
                y += dy; g = {'═': '║', '─': '│', '·': '·'}[style]
            if style == '·':
                g = '·'
            if (x, y) != (bx, by) and (x, y - self.y0) not in terr:
                self._put_map(scr, x, y, g, 'c' if style != '·' else 'd')

    def to_cell_raw(self, scr, wx, wy):
        return self.to_cell(scr, wx, wy)

    def key(self, k, game):
        pan = self.sx() * 4
        if k == pg.K_LEFT:
            self.cx -= pan
        elif k == pg.K_RIGHT:
            self.cx += pan
        elif k == pg.K_UP:
            self.cy -= pan
        elif k == pg.K_DOWN:
            self.cy += pan
        elif k in (pg.K_MINUS, pg.K_KP_MINUS):
            self.scale_i = max(0, self.scale_i - 1)
        elif k in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS):
            self.scale_i = min(2, self.scale_i + 1)
        elif k == pg.K_a:
            self.sel = (self.sel - 1) % len(game.ports)
            self.cx, self.cy = game.ports[self.sel].pos
        elif k == pg.K_d:
            self.sel = (self.sel + 1) % len(game.ports)
            self.cx, self.cy = game.ports[self.sel].pos
        elif k == pg.K_SPACE:
            p = game.ports[self.sel]
            return 'shipyard' if p.shipyard else 'cargo'
        elif k == pg.K_e and not game.ports[self.sel].shipyard:
            return 'portupgrade'
        elif k == pg.K_q:
            return 'quit'
        return 'map'


# ==================================================================== cargo
class CargoView:
    """Manifest left, loading graphic + voyage estimate right."""

    def __init__(self, mapview):
        self.mv = mapview
        self.sec, self.row, self.btn = 'apron', 0, 0
        self.ferry_i = 0

    def port(self, game):
        return game.ports[self.mv.sel]

    def ferry(self, game):
        docked = self.port(game).ferries
        if not docked:
            return None
        self.ferry_i %= len(docked)
        return docked[self.ferry_i]

    # ---------------------------------------------------------------- draw
    def draw(self, scr, game):
        p = self.port(game)
        f = self.ferry(game)
        header(scr, game, p.name.upper(), 'CARGO OPERATIONS')
        if f:
            scr.text(40, 0, f"M/V {f.name}", 'C')
            scr.text(60, 0, f'dock {len(p.ferries)}/{p.cap("docks")}', 'c')
        GX = 60

        scr.text(2, 2, 'DEST', 'c'); scr.text(8, 2, 'CONTENTS', 'c')
        scr.rtext(30, 2, 'PAY', 'c')
        scr.text(33, 2, 'LOAD', 'c'); scr.text(46, 2, 'STAGE', 'c')
        scr.hline(0, 3, GX - 2, '─', 'd')

        hold = f.cargo if f else []
        cap = f.hold_cap() if f else 0
        sections = [('APRON', p.cargo, p.cap('cargo'), 'apron',
                     '[  LOAD  ]', '[  STAGE  ]'),
                    ('STAGED', p.stage, p.cap('stage'), 'stage',
                     '[  LOAD  ]', '[ UNSTAGE ]'),
                    ('HOLD', hold, cap, 'hold', '[ UNLOAD ]', '[  STAGE  ]')]
        lines, cursor_line = [], 0
        for si, (title, items, scap, sec, b1, b2) in enumerate(sections):
            if si:
                lines.append(('sep',))
            lines.append(('head', title, len(items), scap))
            for i, c in enumerate(items):
                if self.sec == sec and self.row == i:
                    cursor_line = len(lines)
                lines.append(('item', sec, i, c, b1, b2))

        top, avail = 4, (scr.rows - 4) - 4
        self.scroll = max(0, min(getattr(self, 'scroll', 0), len(lines) - avail))
        if cursor_line < self.scroll + 1:
            self.scroll = max(0, cursor_line - 1)
        elif cursor_line > self.scroll + avail - 2:
            self.scroll = min(max(0, len(lines) - avail), cursor_line - avail + 2)
        for k, ln in enumerate(lines[self.scroll:self.scroll + avail]):
            y = top + k
            if ln[0] == 'sep':
                scr.hline(0, y, GX - 2, '─', 'd')
            elif ln[0] == 'head':
                _, title, n, scap = ln
                scr.text(1, y, title, 'w')
                scr.text(10, y, '[X]' * n + '[ ]' * max(0, scap - n), 'c')
                scr.rtext(GX - 4, y, f'{n} / {scap}', 'd')
            else:
                _, sec, i, c, b1, b2 = ln
                scr.text(2, y, c.dest.code, 'C')
                scr.text(8, y, c.contents[:18], '_')
                scr.rtext(30, y, f'${c.payment:,}', 'g')
                for bi, lbl in ((0, b1), (1, b2)):
                    on = (self.sec == sec and self.row == i and self.btn == bi)
                    scr.text(33 + bi * 13, y, lbl, 'w' if on else '_',
                             'S' if on else None)
        if self.scroll > 0:
            scr.text(GX - 3, top, '▲', 'C')
        if self.scroll + avail < len(lines):
            scr.text(GX - 3, top + avail - 1, '▼', 'C')

        # ---- right column ------------------------------------------------
        scr.rect(GX, 2, scr.cols - GX, 13, 'c', title='VESSEL')
        if f:
            art.draw_profile(scr, GX + 2, 4, f, cols=scr.cols - GX - 4, rows=9)
            scr.text(GX + 2, 13, f"M/V {f.name}", 'C')
            scr.rtext(scr.cols - 3, 13,
                      f"hold {len(f.cargo)}/{f.hold_cap()}  {f.speed():.0f} kts  "
                      f"${f.eff()}/NM", '_')
        else:
            scr.ctext(GX + (scr.cols - GX) // 2, 8, 'NO VESSEL DOCKED', 'd')
            scr.ctext(GX + (scr.cols - GX) // 2, 10, 'F cycles, or sail one in', 'd')

        yv = 15
        scr.rect(GX, yv, scr.cols - GX, 11, 'c', title='VOYAGE ESTIMATE')
        if f:
            dest = self._plan_dest(game, f)
            if dest:
                d = world.dist(p.pos, dest.pos)
                items = [c for c in f.cargo if c.dest is dest]
                rev = sum(c.payment for c in items)
                bonus = int(rev * 0.05 * max(0, len(items) - 1))
                fuel = int(d * f.eff())
                rows = [('DESTINATION', dest.code, 'C'),
                        ('DISTANCE', f'{d:.1f} NM', '_'),
                        (f'REVENUE  {len(items)} item', f'$ {rev:,}', 'g'),
                        (f'BUNDLE  +{5 * max(0, len(items) - 1)}%', f'$ {bonus:,}', 'g'),
                        (f'FUEL  {d:.1f} x ${f.eff()}', f'$ -{fuel:,}', 'a')]
                for i, (k, v, fg) in enumerate(rows):
                    scr.text(GX + 2, yv + 2 + i, k, 'c')
                    scr.rtext(scr.cols - 3, yv + 2 + i, v, fg)
                scr.hline(GX + 2, yv + 7, scr.cols - GX - 4, '─', 'd')
                net = rev + bonus - fuel
                scr.text(GX + 2, yv + 8, 'NET', 'w')
                scr.rtext(scr.cols - 3, yv + 8, f'$ {net:,}', 'g' if net >= 0 else 'a')
            else:
                scr.ctext(GX + (scr.cols - GX) // 2, yv + 5, 'hold is empty', 'd')

        yp = 27
        scr.rect(GX, yp, scr.cols - GX, 4, 'c', title='PORT')
        scr.text(GX + 2, yp + 1, 'JOBS ROTATE', 'c')
        scr.rtext(scr.cols - 3, yp + 1, f'{int((game.next_jobs - game.t) * 60)} min', 'a')
        scr.text(GX + 2, yp + 2, '[ E ] UPGRADE PORT', 'c')

        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2, '[ Q CLOSE ]', '_')
        scr.text(16, scr.rows - 2, '[ F VESSEL ]', '_')
        scr.text(31, scr.rows - 2, '[ RETURN  DEPART ---> ]',
                 'w' if f else 'd')
        scr.rtext(scr.cols - 2, scr.rows - 2, 'WASD MOVE  SPACE ACT', 'c')
        eventline(scr, game)

    def _plan_dest(self, game, f):
        if not f.cargo:
            return None
        best, n = None, -1
        for p in game.cargo_ports():
            k = sum(1 for c in f.cargo if c.dest is p)
            if k > n and k > 0:
                best, n = p, k
        return best

    # ----------------------------------------------------------------- key
    def key(self, k, game):
        p = self.port(game)
        f = self.ferry(game)
        lists = {'apron': p.cargo, 'stage': p.stage,
                 'hold': f.cargo if f else []}
        order = ['apron', 'stage', 'hold']

        def clamp():
            lst = lists[self.sec]
            if not lst:
                for s in order:
                    if lists[s]:
                        self.sec = s
                        break
            self.row = max(0, min(self.row, len(lists[self.sec]) - 1))

        if k == pg.K_q:
            return 'map'
        if k == pg.K_f:
            self.ferry_i += 1
            return 'cargo'
        if k == pg.K_e:
            return 'portupgrade'
        if k == pg.K_RETURN:
            if f:
                return 'destination'          # empty departure allowed: fuel is real
            return 'cargo'
        if k == pg.K_w:
            if self.row > 0:
                self.row -= 1
            else:
                i = order.index(self.sec)
                for s in reversed(order[:i]):
                    if lists[s]:
                        self.sec, self.row = s, len(lists[s]) - 1
                        break
        elif k == pg.K_s:
            if self.row < len(lists[self.sec]) - 1:
                self.row += 1
            else:
                i = order.index(self.sec)
                for s in order[i + 1:]:
                    if lists[s]:
                        self.sec, self.row = s, 0
                        break
        elif k == pg.K_a:
            self.btn = 0
        elif k == pg.K_d:
            self.btn = 1
        elif k == pg.K_SPACE and lists[self.sec]:
            c = lists[self.sec][self.row]
            if self.sec == 'apron':
                if self.btn == 0 and f and len(f.cargo) < f.hold_cap():
                    p.cargo.remove(c); f.cargo.append(c)
                elif self.btn == 1 and len(p.stage) < p.cap('stage'):
                    p.cargo.remove(c); p.stage.append(c)
            elif self.sec == 'stage':
                if self.btn == 0 and f and len(f.cargo) < f.hold_cap():
                    p.stage.remove(c); f.cargo.append(c)
                elif self.btn == 1 and len(p.cargo) < p.cap('cargo'):
                    p.stage.remove(c); p.cargo.append(c)
            elif self.sec == 'hold' and f:
                if self.btn == 0 and len(p.cargo) < p.cap('cargo'):
                    f.cargo.remove(c); p.cargo.append(c)
                elif self.btn == 1 and len(p.stage) < p.cap('stage'):
                    f.cargo.remove(c); p.stage.append(c)
            p.sort_cargo()
            clamp()
        clamp()
        return 'cargo'


# ============================================================== destination
class DestView:
    def __init__(self, mapview, cargoview):
        self.mv, self.cv = mapview, cargoview
        self.row = 0
        self.back = 'cargo'
        self.override = None            # ferry chosen by the shipyard view

    def ferry(self, game):
        if self.override and not self.override.moving:
            return self.override
        return self.cv.ferry(game)

    def draw(self, scr, game):
        f = self.ferry(game)
        p = f.port if f else game.ports[self.mv.sel]
        header(scr, game, 'SELECT DESTINATION', f'M/V {f.name}' if f else '')
        dests = [d for d in game.ports if d is not p]
        scr.text(2, 3, 'PORT', 'c'); scr.rtext(30, 3, 'DIST', 'c')
        scr.rtext(42, 3, 'FUEL', 'c'); scr.rtext(54, 3, 'REVENUE', 'c')
        scr.rtext(66, 3, 'NET', 'c'); scr.text(70, 3, 'DOCKS', 'c')
        scr.hline(0, 4, scr.cols, '─', 'd')
        for i, d in enumerate(dests):
            y = 5 + i * 2
            dist = world.dist(p.pos, d.pos)
            fuel = int(dist * f.eff()) if f else 0
            items = [c for c in f.cargo if c.dest is d] if f else []
            rev = sum(c.payment for c in items)
            rev = int(rev * (1 + 0.05 * max(0, len(items) - 1)))
            net = rev - fuel
            on = (i == self.row)
            scr.text(2, y, f'[{d.name:^20}]', 'w' if on else '_', 'S' if on else None)
            scr.rtext(30, y, f'{dist:.1f}', '_')
            scr.rtext(42, y, f'-${fuel:,}', 'a')
            scr.rtext(54, y, f'${rev:,}' if items else '--', 'g' if items else 'd')
            scr.rtext(66, y, f'{net:+,}', 'g' if net >= 0 else 'a')
            free = d.berths_free(game)
            scr.text(70, y, 'FULL' if free <= 0 else f'{free} free',
                     'a' if free <= 0 else '_')
            if d.shipyard:
                scr.text(78, y, 'refit & new hulls here', 'd')
        if f:
            slots = '[X]' * len(f.cargo) + '[ ]' * (f.hold_cap() - len(f.cargo))
            scr.ctext(scr.cols // 2, scr.rows - 6, slots, 'c')
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2, 'W/S CHOOSE   SPACE DEPART   Q BACK', 'c')
        eventline(scr, game)

    def key(self, k, game):
        f = self.ferry(game)
        p = f.port if f else game.ports[self.mv.sel]
        dests = [d for d in game.ports if d is not p]
        if k == pg.K_q:
            back, self.back, self.override = self.back, 'cargo', None
            return back
        if k == pg.K_w:
            self.row = (self.row - 1) % len(dests)
        elif k == pg.K_s:
            self.row = (self.row + 1) % len(dests)
        elif k == pg.K_SPACE and f:
            d = dests[self.row]
            if d.berths_free(game) <= 0:
                game.log(f'{d.name} has no free berth (inbound hulls count)', 'a')
            else:
                f.depart(d, game)
                self.back, self.override = 'cargo', None
                return 'map'
        return 'destination'


# ================================================================= upgrades
def upgrade_table(scr, x, y, w, rows, cur, confirming, credits):
    scr.text(x, y, 'ATTRIBUTE', 'c')
    scr.rtext(x + 30, y, 'CURRENT', 'c'); scr.rtext(x + 40, y, 'NEXT', 'c')
    scr.rtext(x + 52, y, 'PRICE', 'c'); scr.text(x + 57, y, 'ACTION', 'c')
    scr.text(x + 72, y, 'LEVEL', 'c')
    scr.hline(x, y + 1, w, '─', 'd')
    for i, (name, curv, nxt, price, lvl, mx) in enumerate(rows):
        yy = y + 2 + i
        can = price is not None and credits >= price
        scr.text(x, yy, name, '_')
        scr.rtext(x + 30, yy, str(curv), 'w')
        scr.rtext(x + 40, yy, str(nxt) if nxt is not None else '---',
                  '_' if can else 'd')
        scr.rtext(x + 52, yy, f'${price:,}' if price else '', 'g' if can else 'd')
        on = (i == cur)
        lbl = '[ CONFIRM ]' if (on and confirming) else '[ UPGRADE ]'
        if price is None:
            lbl = '[  MAX   ]'
        scr.text(x + 57, yy, lbl, 'w' if on else ('_' if can else 'd'),
                 'S' if on else None)
        scr.text(x + 72, yy, '[' + '+' * (lvl + 1) + '-' * (mx - lvl - 1) + ']', 'g')


class PortUpgradeView:
    def __init__(self, mapview):
        self.mv = mapview
        self.row, self.confirm = 0, False

    def draw(self, scr, game):
        p = game.ports[self.mv.sel]
        header(scr, game, p.name.upper(), 'PORT UPGRADE')
        rows = []
        for kind, label in (('cargo', 'Cargo capacity'), ('stage', 'Stage capacity'),
                            ('docks', 'Docks')):
            lvls, prices = PORT_UPG[kind]
            lv = p.lv[kind]
            nxt = lvls[lv + 1] if lv < len(lvls) - 1 else None
            rows.append((label, lvls[lv], nxt, p.upgrade_price(kind), lv, len(lvls)))
        upgrade_table(scr, 3, 4, scr.cols - 6, rows, self.row, self.confirm,
                      game.credits)
        scr.text(3, 12, 'more capacity means more jobs on the apron each rotation', 'd')
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2, 'W/S CHOOSE   SPACE UPGRADE (twice to confirm)   Q BACK', 'c')
        eventline(scr, game)

    def key(self, k, game):
        p = game.ports[self.mv.sel]
        kinds = ['cargo', 'stage', 'docks']
        if k == pg.K_q:
            return 'cargo'
        if k in (pg.K_w, pg.K_s):
            self.row = (self.row + (1 if k == pg.K_s else -1)) % 3
            self.confirm = False
        elif k == pg.K_SPACE:
            kind = kinds[self.row]
            price = p.upgrade_price(kind)
            if price is None or game.credits < price:
                self.confirm = False
            elif not self.confirm:
                self.confirm = True
            else:
                p.lv[kind] += 1
                game.credits -= price
                game.log(f'{p.name} {kind} upgraded, -${price:,}')
                self.confirm = False
        return 'portupgrade'


# ================================================================= shipyard
class ShipyardView:
    def __init__(self, mapview, destview):
        self.mv, self.dv = mapview, destview
        self.sec = 'fleet'               # fleet | refit | market
        self.frow = self.rrow = self.mrow = 0
        self.confirm = False

    def draw(self, scr, game):
        yard = game.shipyard()
        header(scr, game, 'SHIPYARD', 'FLEET & REFIT')
        scr.text(40, 0, f'berths {len(yard.ferries)}/{yard.cap("docks")}', 'c')
        if not game.ferries:
            scr.rect(0, 2, scr.cols, 8, 'c', title='FLEET')
            scr.ctext(scr.cols // 2, 5, 'NO HULLS IN SERVICE', 'a')
            scr.ctext(scr.cols // 2, 7, 'buy one below to resume operations', 'd')
            self._market(scr, game, yard, 12)
            scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
            scr.text(2, scr.rows - 2, 'W/S CHOOSE   SPACE BUY (twice confirms)   Q BACK', 'c')
            eventline(scr, game)
            return

        # ---- fleet -------------------------------------------------------
        scr.rect(0, 2, 44, 10, 'c', title='FLEET')
        scr.text(2, 4, 'HULL', 'c'); scr.text(16, 4, 'CLASS', 'c')
        scr.text(25, 4, 'HOLD', 'c'); scr.rtext(41, 4, 'STATUS', 'c')
        scr.hline(2, 5, 40, '─', 'd')
        for i, f in enumerate(game.ferries[:4]):
            y = 6 + i
            here = f.port is yard and not f.moving
            st, fg = ('AT SEA', '_') if f.moving else \
                     (('HERE', 'g') if here else (f.port.code, 'a'))
            on = (self.sec == 'fleet' and i == self.frow)
            scr.text(2, y, '►', 'g')
            scr.text(4, y, f.name, 'w' if on else '_', 'S' if on else None)
            scr.text(16, y, f.cls, '_')
            scr.text(25, y, f'{len(f.cargo)}/{f.hold_cap()}', 'c')
            scr.rtext(41, y, st, fg)

        f = game.ferries[self.frow % len(game.ferries)]
        here = f.port is yard and not f.moving

        # ---- plan --------------------------------------------------------
        scr.rect(44, 2, 15, 21, 'c', title='PLAN')
        art.draw_plan(scr, 47, 4, f, cols=9, rows=17)

        # ---- selected stats ---------------------------------------------
        scr.rect(59, 2, scr.cols - 59, 10, 'c', title='SELECTED')
        stats = [('HULL', f'M/V {f.name}', 'C'), ('CLASS', f.cls, '_'),
                 ('HOLD', f'{f.hold_cap()} slots', '_'),
                 ('SPEED', f'{f.speed():.1f} kts', '_'),
                 ('EFFICIENCY', f'${f.eff()} / NM', 'a'),
                 ('STATUS', 'IN YARD' if here else 'NOT HERE', 'g' if here else 'a')]
        for i, (k, v, fg) in enumerate(stats):
            scr.text(61, 4 + i, k, 'c')
            scr.rtext(scr.cols - 3, 4 + i, v, fg)

        # ---- refit -------------------------------------------------------
        scr.rect(0, 12, 44, 11, 'c', title=f'REFIT  M/V {f.name}')
        rows = []
        for k, label, unit in (('hold', 'Hold', ' slots'), ('spd', 'Speed', ' kts'),
                               ('eff', 'Efficiency', ' $/NM')):
            import sim
            arr = sim.CLASSES[f.cls][k]
            lv = f.lv[k]
            nxt = arr[lv + 1] if lv < len(arr) - 1 else None
            rows.append((label + unit, arr[lv], nxt, f.upgrade_price(k),
                         lv, len(arr)))
        self._refit_table(scr, 2, 14, rows, game, here)
        if not here:
            scr.text(2, 21, 'sail her to the yard to refit', 'a')

        # ---- market ------------------------------------------------------
        self._market(scr, game, yard, 12)

        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'TAB SECTION   W/S CHOOSE   SPACE ACT (twice confirms)   '
                 'RETURN DEPART   Q BACK', 'c')
        scr.rtext(scr.cols - 2, scr.rows - 2,
                  ['FLEET', 'REFIT', 'MARKET'][['fleet', 'refit', 'market']
                                               .index(self.sec)] + ' <', 'w')
        eventline(scr, game)

    def _market(self, scr, game, yard, top):
        import sim
        x = 59 if game.ferries else 0
        w = scr.cols - x
        scr.rect(x, top, w, 11, 'c', title='NEW HULLS')
        scr.text(x + 2, top + 2, 'CLASS', 'c')
        scr.rtext(x + 17, top + 2, 'HOLD', 'c'); scr.rtext(x + 25, top + 2, 'KTS', 'c')
        scr.rtext(x + 33, top + 2, '$/NM', 'c'); scr.rtext(x + 43, top + 2, 'PRICE', 'c')
        berth = yard.berths_free(game) > 0
        for i, (name, spec) in enumerate(sim.CLASSES.items()):
            y = top + 3 + i
            can = game.credits >= spec['price'] and berth
            on = (self.sec == 'market' and i == self.mrow)
            lbl = name
            if on and self.confirm and can:
                lbl = f'{name}  CONFIRM?'
            scr.text(x + 2, y, lbl, 'w' if on else ('_' if can else 'd'),
                     'S' if on else None)
            scr.rtext(x + 17, y, str(spec['hold'][0]), '_' if can else 'd')
            scr.rtext(x + 25, y, f"{spec['spd'][0]:.0f}", '_' if can else 'd')
            scr.rtext(x + 33, y, str(spec['eff'][0]), '_' if can else 'd')
            scr.rtext(x + 43, y, f"${spec['price']:,}", 'g' if can else 'd')
        note = 'berth required to take delivery' if berth is False else \
            ('accounts in arrears -- clear them first' if game.credits < 0
             else 'delivered to a free berth here')
        scr.text(x + 2, top + 8, note, 'a' if (not berth or game.credits < 0) else 'd')

    def _refit_table(self, scr, x, y, rows, game, here):
        for i, (name, curv, nxt, price, lv, mx) in enumerate(rows):
            yy = y + 1 + i * 2
            can = here and price is not None and game.credits >= price
            on = (self.sec == 'refit' and i == self.rrow)
            scr.text(x, yy, name, '_')
            scr.rtext(x + 19, yy, str(curv), 'w')
            scr.text(x + 20, yy, '>', 'd')
            scr.rtext(x + 26, yy, str(nxt) if nxt is not None else '--',
                      '_' if can else 'd')
            lbl = '[ CONFIRM ]' if (on and self.confirm) else '[ UPGRADE ]'
            if price is None:
                lbl = '[   MAX   ]'
            scr.text(x + 28, yy, lbl, 'w' if on else ('_' if can else 'd'),
                     'S' if on else None)
            if price:
                scr.rtext(x + 38, yy + 1, f'${price:,}', 'g' if can else 'd')

    def key(self, k, game):
        import sim
        yard = game.shipyard()
        if not game.ferries:                      # fleet lost: market only
            self.sec = 'market'
            if k == pg.K_q:
                return 'map'
            if k in (pg.K_w, pg.K_s):
                self.mrow = (self.mrow + (1 if k == pg.K_s else -1)) % len(sim.CLASSES)
                self.confirm = False
            elif k == pg.K_SPACE:
                self._buy(game, yard)
            return 'shipyard'
        f = game.ferries[self.frow % len(game.ferries)]
        here = f.port is yard and not f.moving
        if k == pg.K_q:
            return 'map'
        if k == pg.K_RETURN:
            if here:
                self.dv.override = f
                self.dv.back = 'shipyard'
                return 'destination'
            game.log(f'{f.name} is not at the yard', 'a')
            return 'shipyard'
        if k == pg.K_TAB:
            order = ['fleet', 'refit', 'market']
            self.sec = order[(order.index(self.sec) + 1) % 3]
            self.confirm = False
        elif k in (pg.K_w, pg.K_s):
            d = 1 if k == pg.K_s else -1
            if self.sec == 'fleet':
                self.frow = (self.frow + d) % len(game.ferries)
            elif self.sec == 'refit':
                self.rrow = (self.rrow + d) % 3
            else:
                self.mrow = (self.mrow + d) % len(sim.CLASSES)
            self.confirm = False
        elif k == pg.K_SPACE:
            if self.sec == 'refit':
                kind = ['hold', 'spd', 'eff'][self.rrow]
                price = f.upgrade_price(kind)
                if not here or price is None or game.credits < price:
                    self.confirm = False
                elif not self.confirm:
                    self.confirm = True
                else:
                    f.lv[kind] += 1
                    game.credits -= price
                    game.log(f'{f.name} {kind} refit complete, -${price:,}')
                    self.confirm = False
            elif self.sec == 'market':
                self._buy(game, yard)
        return 'shipyard'

    def _buy(self, game, yard):
        import random
        import sim
        name = list(sim.CLASSES)[self.mrow]
        spec = sim.CLASSES[name]
        if game.credits < spec['price'] or yard.berths_free(game) <= 0:
            self.confirm = False
            return
        if not self.confirm:
            self.confirm = True
            return
        pool = ['RESOLUTE', 'TEMPEST', 'AURORA', 'CORMORANT', 'VIGIL',
                'HALCYON', 'MERIDIAN', 'SENTINEL', 'PILGRIM', 'BEACON']
        taken = {f.name for f in game.ferries}
        free = [n for n in pool if n not in taken]
        nm = random.choice(free) if free else f'HULL-{len(game.ferries) + 1}'
        game.ferries.append(sim.Ferry(nm, name, yard))
        game.credits -= spec['price']
        game.log(f'M/V {nm} ({name}) delivered, -${spec["price"]:,}')
        self.confirm = False
