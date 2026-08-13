"""Views. Each has draw(scr, game) and key(k, game) -> next view name.

Time never passes inside a view -- the world advances only when the map
returns 'tick' or 'run' to the main loop. Dock work is free; attention is
what the interface spends.

Uncertainty lives in the world, never in the interface: every quote on a
commit screen is exact, and the only thing the map refuses to tell you is
what the unstable water is hiding.
"""
import math
import pygame as pg

import art
import routes
import world
from sim import (PORT_UPG, CLASSES, COMPONENTS, REFRESH,
                 BUOY_PRICE, BUOY_UPKEEP)


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
        scr.text(1, scr.rows - 1, f"T{t:04d}  {msg}"[:scr.cols - 2], fg)


def bearing(a, b):
    return int(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) + 90) % 360


def comp_str(f, wide=True):
    if wide:
        return '  '.join(f"{k} {f.components[k]:3d}" for k in COMPONENTS)
    return ' '.join(f"{k[0]}{f.components[k]:<3d}" for k in COMPONENTS)


def ship_status(f, game):
    if f.derelict:
        return ('DERELICT', 'm')
    if f.port is not None:
        return (f"docked {f.port.code}", '_')
    if f.queue and f.queue[0]['kind'] == 'leg':
        o = f.queue[0]
        t = math.ceil((o['nm'] - o['done']) / max(0.01, f.speed_pt()))
        return (f"leg->{o['dest'] or 'sea'} {t}t", '_')
    if f.queue and f.queue[0]['kind'] == 'tow':
        return (f"tow {f.queue[0]['target']}", '_')
    return ('HOLDING in open water', 'a')


# ======================================================================= map
class MapView:
    SCALES = [1.06, 0.42, 0.18]
    RUN_HELP = ('ARROWS PAN  -/+ RANGE  A/D PORT  TAB SHIP',
                'E OPEN  U UPGRADE  O OBSERVE  R ROUTE  I HULL',
                'X ABANDON  SPACE TICK  RETURN RUN  F5/F9  Q QUIT')

    def __init__(self):
        self.scale_i = 0
        self.cx, self.cy = 56.0, 18.0
        self.sel = 0                     # selected port index
        self.sel_ship = 0                # selected hull index
        self.confirm_x = False           # two-press abandon
        self._terrain = {}
        self._shade = None
        self._shade_key = None
        self.y0, self.mh = 2, 0
        self.anim = 0.0                  # wall-clock flicker phase

    # ---- projection ------------------------------------------------------
    def sx(self):
        return self.SCALES[self.scale_i]

    def to_cell(self, scr, wx, wy):
        sx = self.sx(); sy = sx * (scr.ch / scr.cw)
        x0 = self.cx - sx * scr.cols / 2
        y0 = self.cy - sy * self.mh / 2
        return int(round((wx - x0) / sx)), int(round((wy - y0) / sy)) + self.y0

    def ship(self, game):
        if not game.ships:
            return None
        self.sel_ship %= len(game.ships)
        return game.ships[self.sel_ship]

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

        # ---- how-decided shading (recomputed when the tick moves) --------
        skey = (tkey, game.tick_no)
        if self._shade_key != skey:
            shade = {}
            for cy in range(self.mh):
                for cx in range(scr.cols):
                    if (cx, cy) in terr:
                        continue
                    wx, wy = x0 + (cx + 0.5) * sx, y0 + (cy + 0.5) * sy
                    s = game.stability(wx, wy)
                    if s < 4:
                        shade[(cx, cy)] = s
            self._shade, self._shade_key = shade, skey
        frame = int(self.anim * 9)
        for (cx, cy), s in self._shade.items():
            if s == 3:
                g = '░'                          # settled: holds still
            else:                                # unresolved water flickers
                r = (cx * 7 + cy * 13 + frame) % 11
                g = ('░▒░' if s == 2 else '▒▓▒' if s == 1 else '▓▒▓')[
                    0 if r > 1 else (1 if r == 0 else 2)]
            scr.put(cx, cy + self.y0, g, 'd')

        # ---- lanes: solid where the water is bought, dotted where not ----
        lit = set(routes.PORTS) | game.buoys
        for a, b in routes.EDGES:
            style = '═' if a in lit and b in lit else '·'
            self._route(scr, routes.NODES[a], routes.NODES[b], style, terr)

        # ---- stations ----------------------------------------------------
        for nid, pos in routes.NODES.items():
            if nid in routes.PORTS:
                continue
            px, py = self.to_cell(scr, *pos)
            if nid in game.buoys:
                self._put_map(scr, px, py, '○', 'c')
            else:
                self._put_map(scr, px, py, '·', 'd')
        for i, p in enumerate(game.ports):
            px, py = self.to_cell(scr, *p.pos)
            sel = (i == self.sel)
            self._put_map(scr, px, py, '⌂', 'w' if sel else 'C')
            self._text_map(scr, px - 1, py + 1, p.code, 'w' if sel else 'C',
                           'S' if sel else None)

        # ---- hulls -------------------------------------------------------
        for i, f in enumerate(game.ships):
            px, py = self.to_cell(scr, *f.pos)
            if f.derelict:
                self._put_map(scr, px, py, '×', 'm')
            else:
                hx, hy = f.heading
                g = '►' if abs(hx) >= abs(hy) and hx >= 0 else \
                    '◄' if abs(hx) >= abs(hy) else ('▼' if hy > 0 else '▲')
                fg = 'w' if i == self.sel_ship else 'g'
                self._put_map(scr, px, py, g, fg)
                if game.observed is f:
                    self._put_map(scr, px - 1, py, '[', 'g')
                    self._put_map(scr, px + 1, py, ']', 'g')
            if self.scale_i > 0:
                self._text_map(scr, px + 2, py, f.name,
                               'm' if f.derelict else 'g')

        # ---- the contact the array cannot decide -------------------------
        rep = game.anomaly_report()
        if rep:
            ax, ay = self.to_cell(scr, rep[0], rep[1])
            self._put_map(scr, ax, ay, '?', 'm')
            if self.scale_i > 0 or rep[2] > 0:
                tag = 'UNRESOLVED' if rep[2] == 0 else f'LAST SEEN T-{rep[2]}'
                self._text_map(scr, ax + 2, ay, tag, 'm')

        # ---- chrome ------------------------------------------------------
        header(scr, game, 'PUGET SOUND OPERATING AREA')
        scr.text(30, 0, 'SCALE', 'c')
        scr.text(36, 0, ['STRATEGIC', 'REGIONAL', 'TACTICAL'][self.scale_i], 'w')
        scr.text(48, 0, 'ARRAY', 'c')
        if game.dropout:
            scr.text(54, 0, '[DROPOUT]', 'm')
        elif game.observed:
            scr.text(54, 0, f'[OBS {game.observed.name[:9]}]', 'g')
        else:
            scr.text(54, 0, '[UNFLAGGED]', 'c')

        fy = scr.rows - 5
        scr.hline(0, fy, scr.cols, '═', 'c')
        scr.text(1, fy + 1, 'CONTACTS', 'c')
        sp = game.ports[self.sel]
        rows_avail = 3
        entries = []
        for i, f in enumerate(game.ships):
            st, sfg = ship_status(f, game)
            mark = '×' if f.derelict else '►'
            nfg = 'w' if i == self.sel_ship else \
                ('m' if f.derelict else '_')
            obs = ' [OBS]' if game.observed is f else ''
            entries.append((mark, 'm' if f.derelict else 'g', f.name, nfg,
                            f"{comp_str(f, wide=False)}  {st}{obs}"[:31], sfg))
        if rep:
            entries = entries[:rows_avail - 1]
            stale = '' if rep[2] == 0 else f'  stale {rep[2]}t'
            entries.append(('?', 'm', 'UNRESOLVED', 'm',
                            f"brg {bearing(sp.pos, rep[:2]):03d}  "
                            f"{world.dist(sp.pos, rep[:2]):5.1f} NM  "
                            f"radar/sonar disagree{stale}", 'a'))
        shown = entries[:rows_avail]
        for i, (g, gfg, name, nfg, st, sfg) in enumerate(shown):
            scr.text(12, fy + 1 + i, g, gfg)
            scr.text(14, fy + 1 + i, name, nfg)
            scr.text(26, fy + 1 + i, st, sfg)
        for i, s in enumerate(self.RUN_HELP):
            scr.rtext(scr.cols - 2, fy + 1 + i, s, 'c')
        eventline(scr, game)

    def _put_map(self, scr, x, y, ch, fg):
        if 0 <= x < scr.cols and self.y0 <= y < self.y0 + self.mh:
            scr.put(x, y, ch, fg)

    def _text_map(self, scr, x, y, s, fg, bg=None):
        if self.y0 <= y < self.y0 + self.mh:
            scr.text(x, y, s, fg, bg)

    def _route(self, scr, a, b, style, terr):
        ax, ay = self.to_cell(scr, *a)
        bx, by = self.to_cell(scr, *b)
        dx = (bx > ax) - (bx < ax); dy = (by > ay) - (by < ay)
        x, y, guard = ax, ay, 0
        while (x, y) != (bx, by) and guard < 500:
            guard += 1
            if x != bx and y != by:
                x += dx; y += dy
                g = '\\' if dx == dy else '/'
            elif x != bx:
                x += dx; g = style
            else:
                y += dy; g = {'═': '║', '·': '·'}[style]
            if style == '·':
                g = '·'
            if (x, y) != (bx, by) and (x, y - self.y0) not in terr:
                self._put_map(scr, x, y, g, 'c' if style != '·' else 'd')

    def key(self, k, game):
        pan = self.sx() * 4
        f = self.ship(game)
        if k not in (pg.K_x,):
            self.confirm_x = False
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
        elif k == pg.K_TAB and game.ships:
            self.sel_ship = (self.sel_ship + 1) % len(game.ships)
            f = game.ships[self.sel_ship]
            self.cx, self.cy = f.pos
        elif k == pg.K_e:
            p = game.ports[self.sel]
            return 'shipyard' if p.shipyard else 'cargo'
        elif k == pg.K_u and not game.ports[self.sel].shipyard:
            return 'portupgrade'
        elif k == pg.K_o and f and not f.derelict:
            game.set_observed(f)
        elif k == pg.K_r and f and not f.derelict:
            return 'route'
        elif k == pg.K_i and f:
            return 'inhull'
        elif k == pg.K_x and f:
            live = [c for c in f.cargo if not c.void]
            if not live:
                game.log(f"{f.name} carries nothing to abandon")
            elif not self.confirm_x:
                self.confirm_x = True
                game.log(f"abandon {len(live)} contract(s) aboard {f.name}? "
                         f"X again to confirm", 'a')
            else:
                self.confirm_x = False
                game.abandon(f)
        elif k == pg.K_SPACE:
            return 'tick'
        elif k == pg.K_RETURN:
            return 'run'
        elif k == pg.K_F5:
            game.save()
            game.log("state committed to disk")
        elif k == pg.K_F9:
            return 'load'
        elif k == pg.K_q:
            return 'quit'
        return 'map'


# ==================================================================== cargo
class CargoView:
    """Manifest left, loading graphic + committed-cost quote right."""

    def __init__(self, mapview):
        self.mv = mapview
        self.sec, self.row, self.btn = 'apron', 0, 0
        self.ferry_i = 0

    def port(self, game):
        return game.ports[self.mv.sel]

    def ferry(self, game):
        docked = [f for f in self.port(game).ferries if not f.derelict]
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
        GX = 62

        scr.text(2, 2, 'DEST', 'c'); scr.text(8, 2, 'CONTENTS', 'c')
        scr.rtext(27, 2, 'PAY', 'c'); scr.rtext(33, 2, 'WIN', 'c')
        scr.text(36, 2, 'LOAD', 'c'); scr.text(48, 2, 'STAGE', 'c')
        scr.hline(0, 3, GX - 2, '─', 'd')

        hold = f.cargo if f else []
        cap = f.hold_cap() if f else 0
        sections = [('APRON', p.cargo, p.cap('cargo'), 'apron',
                     '[  LOAD  ]', '[ STAGE  ]'),
                    ('STAGED', p.stage, p.cap('stage'), 'stage',
                     '[  LOAD  ]', '[UNSTAGE ]'),
                    ('HOLD', hold, cap, 'hold', '[ UNLOAD ]', '[ STAGE  ]')]
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
        for kk, ln in enumerate(lines[self.scroll:self.scroll + avail]):
            y = top + kk
            if ln[0] == 'sep':
                scr.hline(0, y, GX - 2, '─', 'd')
            elif ln[0] == 'head':
                _, title, n, scap = ln
                scr.text(1, y, title, 'w')
                scr.text(10, y, '[X]' * n + '[ ]' * max(0, scap - n), 'c')
                scr.rtext(GX - 4, y, f'{n} / {scap}', 'd')
            else:
                _, sec, i, c, b1, b2 = ln
                if c.void:
                    scr.text(2, y, '---', 'm')
                    scr.text(8, y, 'VOID -- decohered', 'm')
                    continue
                scr.text(2, y, c.dest.code, 'C')
                scr.text(8, y, c.contents[:16], '_')
                scr.rtext(27, y, f'${c.payment:,}', 'g')
                wfg = 'a' if c.window <= 8 else '_'
                scr.rtext(33, y, str(c.window), wfg)
                if c.priority:
                    scr.text(6, y, '!', 'a')
                for bi, lbl in ((0, b1), (1, b2)):
                    on = (self.sec == sec and self.row == i and self.btn == bi)
                    scr.text(36 + bi * 12, y, lbl, 'w' if on else '_',
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
            scr.rtext(scr.cols - 3, 13, comp_str(f), '_')
        else:
            scr.ctext(GX + (scr.cols - GX) // 2, 8, 'NO VESSEL DOCKED', 'd')
            scr.ctext(GX + (scr.cols - GX) // 2, 10, 'F cycles, or sail one in', 'd')

        yv = 15
        scr.rect(GX, yv, scr.cols - GX, 11, 'c', title='BEST QUOTE')
        if f:
            dest = self._plan_dest(game, f)
            if dest:
                opts = routes.options(p.code, dest.code, game.water_for(f))
                o = opts[0]
                items = [c for c in f.cargo if c.dest is dest and not c.void]
                rev = sum(c.payment for c in items)
                bonus = int(rev * 0.05 * max(0, len(items) - 1))
                ticks = o.ticks(f.speed_pt())
                fuel = o.fuel(f.eff())
                minw = min((c.window for c in items), default=None)
                rows = [('DESTINATION', dest.code, 'C'),
                        (f'{o.name}', f'{o.nm:.1f} NM / {ticks} ticks', '_'),
                        ('STABILITY', f'{o.stability(game.water_for(f))}/4', '_'),
                        (f'REVENUE  {len(items)} item', f'$ {rev + bonus:,}', 'g'),
                        (f'FUEL', f'$ -{fuel:,}', 'a')]
                for i, (kk, v, fg) in enumerate(rows):
                    scr.text(GX + 2, yv + 2 + i, kk, 'c')
                    scr.rtext(scr.cols - 3, yv + 2 + i, v, fg)
                scr.hline(GX + 2, yv + 7, scr.cols - GX - 4, '─', 'd')
                net = rev + bonus - fuel
                scr.text(GX + 2, yv + 8, 'NET', 'w')
                scr.rtext(scr.cols - 3, yv + 8, f'$ {net:,}', 'g' if net >= 0 else 'a')
                if minw is not None and minw < ticks:
                    scr.text(GX + 2, yv + 9, f'WINDOW {minw} < {ticks} TICKS -- '
                             f'WILL MISS', 'a')
            else:
                scr.ctext(GX + (scr.cols - GX) // 2, yv + 5, 'hold is empty', 'd')

        yp = 27
        scr.rect(GX, yp, scr.cols - GX, 4, 'c', title='PORT')
        scr.text(GX + 2, yp + 1, 'ROTATION', 'c')
        scr.rtext(scr.cols - 14, yp + 1,
                  f'{REFRESH - game.tick_no % REFRESH} ticks', 'a')
        sfg = 'g' if p.standing >= 65 else ('a' if p.standing < 40 else '_')
        scr.text(GX + 2, yp + 2, 'STANDING', 'c')
        scr.rtext(scr.cols - 14, yp + 2, str(p.standing), sfg)
        scr.rtext(scr.cols - 3, yp + 1, '[U]PGRADE', 'c')
        scr.rtext(scr.cols - 3, yp + 2, '[R]EPAIR', 'c')

        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2, '[ Q CLOSE ]', '_')
        scr.text(16, scr.rows - 2, '[ F VESSEL ]', '_')
        scr.text(31, scr.rows - 2, '[ RETURN  COMMIT LEG ---> ]',
                 'w' if f else 'd')
        scr.rtext(scr.cols - 2, scr.rows - 2, 'WASD MOVE  SPACE ACT', 'c')
        eventline(scr, game)

    def _plan_dest(self, game, f):
        live = [c for c in f.cargo if not c.void]
        if not live:
            return None
        best, n = None, -1
        for p in game.cargo_ports() + [game.shipyard()]:
            kk = sum(1 for c in live if c.dest is p)
            if kk > n and kk > 0:
                best, n = p, kk
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
        if k == pg.K_u:
            return 'portupgrade'
        if k == pg.K_r:
            return 'repair' if f else 'cargo'
        if k == pg.K_RETURN:
            if f:
                self.mv.sel_ship = game.ships.index(f)
                return 'route'
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
            if c.void:
                pass                      # a void slot only clears ashore
            elif self.sec == 'apron':
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


# =============================================================== leg commit
class RouteView:
    """The commit screen: every cost exact, every risk a stated band.
    What is *in* the unstable water is never shown here."""

    def __init__(self, mapview):
        self.mv = mapview
        self.drow = 0                    # destination row
        self.orow = 0                    # option row
        self.back = 'map'
        self.confirm_x = False

    def ship(self, game):
        return self.mv.ship(game)

    def _dests(self, game, f):
        home = f.port
        out = [p for p in game.ports if p is not home]
        out += game.wrecks()
        return out

    def _options(self, game, f, dest):
        w = game.water_for(f)
        if hasattr(dest, 'derelict'):    # a wreck: the only offer is a tow
            return None
        start = f.port.code if f.port else tuple(f.pos)
        return routes.options(start, dest.code, w)

    def draw(self, scr, game):
        f = self.ship(game)
        if f is None or f.derelict:
            header(scr, game, 'COMMIT LEG')
            scr.ctext(scr.cols // 2, 10, 'NO HULL SELECTED', 'd')
            eventline(scr, game)
            return
        header(scr, game, 'COMMIT LEG', f'M/V {f.name}')
        live = [c for c in f.cargo if not c.void]
        hold_val = sum(c.payment for c in live)
        scr.rtext(scr.cols - 30, 0, f"HULL {f.components['HUL']}%",
                  'g' if f.components['HUL'] > 60 else 'a')

        dests = self._dests(game, f)
        self.drow %= len(dests)
        scr.text(2, 3, 'DESTINATION', 'c')
        scr.hline(0, 4, 40, '─', 'd')
        for i, d in enumerate(dests):
            y = 5 + i * 2
            on = (i == self.drow)
            wreck = hasattr(d, 'derelict')
            label = f'WRECK OF {d.name}' if wreck else d.name
            scr.text(2, y, f'[{label:^24}]', ('m' if wreck else 'w') if on
                     else ('m' if wreck else '_'), 'S' if on else None)
            if not wreck:
                free = d.berths_free(game)
                scr.text(30, y, 'FULL' if free <= 0 else f'{free} berth',
                         'a' if free <= 0 else 'd')

        dest = dests[self.drow]
        wreck = hasattr(dest, 'derelict')

        # ---- the quote panel --------------------------------------------
        QX = 44
        scr.text(QX, 3, f'LEG -> {("WRECK " + dest.name) if wreck else dest.name.upper()}',
                 'w')
        scr.rtext(scr.cols - 3, 3, f'HOLD ${hold_val:,}  '
                  f'{len(live)}/{f.hold_cap()}', 'c')
        scr.hline(QX, 4, scr.cols - QX - 2, '─', 'c')
        spd = f.speed_pt()
        if wreck:
            out_nm = world.dist(f.pos if f.port is None else f.port.pos, dest.pos)
            back_nm = world.dist(dest.pos, game.shipyard().pos)
            est = math.ceil(out_nm / spd) + math.ceil(back_nm / (spd * 0.5))
            scr.text(QX, 6, '[1] TOW & RETURN TO YARD', 'w', 'S')
            scr.rtext(scr.cols - 3, 6, f'~{est} ticks  '
                      f'${int((out_nm + back_nm) * f.eff()):,} fuel', '_')
            scr.text(QX, 8, 'a wreck holds no cargo and keeps no schedule', 'd')
            self.orow = 0
            opts = ['tow']
        else:
            opts = self._options(game, f, dest)
            self.orow %= max(1, len(opts))
            w = game.water_for(f)
            for i, o in enumerate(opts):
                y = 6 + i * 2
                on = (i == self.orow)
                t = o.ticks(spd)
                s = o.stability(w)
                sfg = 'g' if s >= 3 else ('a' if s >= 2 else 'm')
                scr.text(QX, y, f'[{i + 1}] {o.name:<7}', 'w' if on else '_',
                         'S' if on else None)
                scr.text(QX + 12, y, f'{t:2d} ticks', '_')
                scr.rtext(QX + 32, y, f'${o.fuel(f.eff()):,} fuel', '_')
                scr.rtext(scr.cols - 3, y, f'STABILITY {s}/4', sfg)
                if s <= 1:
                    scr.text(QX + 12, y + 1, 'the water there is not decided',
                             'm')
        scr.hline(QX, 14, scr.cols - QX - 2, '─', 'c')
        minw = min((c.window for c in live), default=None)
        if minw is not None:
            scr.text(QX, 15, f'CONTRACT WINDOW: {minw} ticks remaining',
                     'a' if minw <= 8 else 'c')
        if live:
            cost = sum(6 + int(12 * (1.0 - min(1.0, world.dist(
                f.pos, c.dest.pos) / max(0.1, world.dist(c.src.pos, c.dest.pos)))))
                for c in live)
            scr.text(QX, 16, f'[X] ABANDON'
                     f'{" -- CONFIRM?" if self.confirm_x else ""}', 'a')
            scr.rtext(scr.cols - 3, 16, f'-{cost} STANDING', 'a')

        if f.queue:
            scr.text(2, scr.rows - 6, f'queue: {len(f.queue)} order(s), '
                     f'{f.eta_ticks()} tick(s) committed', 'c')
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'W/S DEST   A/D OPTION   SPACE COMMIT   X ABANDON   Q BACK', 'c')
        eventline(scr, game)

    def key(self, k, game):
        f = self.ship(game)
        if f is None or f.derelict:
            return self.back if k == pg.K_q else 'route'
        if k not in (pg.K_x,):
            self.confirm_x = False
        dests = self._dests(game, f)
        if k == pg.K_q:
            back, self.back = self.back, 'map'
            return back
        if k == pg.K_w:
            self.drow = (self.drow - 1) % len(dests)
            self.orow = 0
        elif k == pg.K_s:
            self.drow = (self.drow + 1) % len(dests)
            self.orow = 0
        elif k in (pg.K_a, pg.K_d):
            self.orow += 1 if k == pg.K_d else -1
        elif k == pg.K_x:
            live = [c for c in f.cargo if not c.void]
            if live and not self.confirm_x:
                self.confirm_x = True
            elif live:
                game.abandon(f)
                self.confirm_x = False
        elif k == pg.K_SPACE:
            dest = dests[self.drow % len(dests)]
            if hasattr(dest, 'derelict'):
                f.enqueue_tow(dest, game)
                self.back = 'map'
                return 'map'
            if dest.berths_free(game) <= 0:
                game.log(f'{dest.name} has no free berth (inbound counts)', 'a')
                return 'route'
            opts = self._options(game, f, dest)
            if not opts:
                game.log('no navigable route offered', 'a')
                return 'route'
            o = opts[self.orow % len(opts)]
            f.enqueue_leg(o, dest.code, game)
            self.back = 'map'
            return 'map'
        return 'route'


# =================================================================== repair
class RepairView:
    """Repair costs ticks in a berth -- the same currency the windows bill."""

    def __init__(self, mapview, cargoview):
        self.mv, self.cv = mapview, cargoview
        self.row = 0
        self.confirm = False
        self.back = 'cargo'

    def ship(self, game):
        return self.cv.ferry(game) or self._any_docked(game)

    def _any_docked(self, game):
        p = game.ports[self.mv.sel]
        return p.ferries[0] if p.ferries else None

    def draw(self, scr, game):
        f = self.ship(game)
        header(scr, game, 'REPAIR BAY',
               f'M/V {f.name}' if f else '')
        if not f:
            scr.ctext(scr.cols // 2, 10, 'NO HULL IN A BERTH HERE', 'd')
            eventline(scr, game)
            return
        scr.text(2, 3, 'COMPONENT', 'c'); scr.rtext(30, 3, 'STATE', 'c')
        scr.rtext(44, 3, 'TICKS', 'c'); scr.rtext(56, 3, 'PARTS $', 'c')
        scr.text(60, 3, 'ACTION', 'c')
        scr.hline(0, 4, scr.cols, '─', 'd')
        names = dict(ENG='Engine', RDR='Radar array', HUL='Hull frames')
        for i, comp in enumerate(COMPONENTS):
            y = 6 + i * 2
            v = f.components[comp]
            q = f.repair_quote(comp)
            on = (i == self.row)
            bar = '[' + '#' * (v // 10) + '.' * (10 - v // 10) + ']'
            vfg = 'g' if v > 60 else ('a' if v > 25 else 'm')
            scr.text(2, y, names[comp], '_')
            scr.rtext(30, y, f'{v:3d} {bar}', vfg)
            if q:
                can = game.credits >= q[1] and not game.in_arrears
                scr.rtext(44, y, str(q[0]), '_' if can else 'd')
                scr.rtext(56, y, f'${q[1]:,}', 'g' if can else 'd')
                lbl = '[ CONFIRM ]' if (on and self.confirm) else '[ REPAIR  ]'
                scr.text(60, y, lbl, 'w' if on else ('_' if can else 'd'),
                         'S' if on else None)
            else:
                scr.rtext(44, y, '--', 'd')
                scr.text(60, y, '[  SOUND  ]', 'd')
        if f.derelict:
            scr.text(2, 14, 'DERELICT: she answers nothing until the hull '
                     'frames are rebuilt', 'm')
        queued = [o for o in f.queue if o['kind'] == 'repair']
        if queued:
            scr.text(2, 16, f'repair queue: ' + ', '.join(
                f"{o['comp']} {o['ticks']}t" for o in queued), 'c')
            scr.text(2, 17, 'the berth is held while the yardbirds work -- '
                     'ticks pass on the map', 'd')
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'W/S CHOOSE   SPACE REPAIR (twice confirms)   Q BACK', 'c')
        eventline(scr, game)

    def key(self, k, game):
        f = self.ship(game)
        if k == pg.K_q:
            back, self.back = self.back, 'cargo'
            return back
        if not f:
            return 'repair'
        if k in (pg.K_w, pg.K_s):
            self.row = (self.row + (1 if k == pg.K_s else -1)) % len(COMPONENTS)
            self.confirm = False
        elif k == pg.K_SPACE:
            comp = COMPONENTS[self.row]
            q = f.repair_quote(comp)
            if q is None or game.credits < q[1] or game.in_arrears:
                self.confirm = False
            elif not self.confirm:
                self.confirm = True
            else:
                f.enqueue_repair(comp, game)
                self.confirm = False
        return 'repair'


# ================================================================= upgrades
class PortUpgradeView:
    def __init__(self, mapview):
        self.mv = mapview
        self.row, self.confirm = 0, False

    def draw(self, scr, game):
        p = game.ports[self.mv.sel]
        header(scr, game, p.name.upper(), 'PORT UPGRADE')
        scr.text(3, 3, 'ATTRIBUTE', 'c')
        scr.rtext(33, 3, 'CURRENT', 'c'); scr.rtext(43, 3, 'NEXT', 'c')
        scr.rtext(55, 3, 'PRICE', 'c'); scr.text(60, 3, 'ACTION', 'c')
        scr.hline(3, 4, scr.cols - 6, '─', 'd')
        for i, (kind, label) in enumerate((('cargo', 'Cargo capacity'),
                                           ('stage', 'Stage capacity'),
                                           ('docks', 'Docks'))):
            y = 5 + i
            lvls, prices = PORT_UPG[kind]
            lv = p.lv[kind]
            nxt = lvls[lv + 1] if lv < len(lvls) - 1 else None
            price = p.upgrade_price(kind)
            can = price is not None and game.credits >= price \
                and not game.in_arrears
            on = (i == self.row)
            scr.text(3, y, label, '_')
            scr.rtext(33, y, str(lvls[lv]), 'w')
            scr.rtext(43, y, str(nxt) if nxt is not None else '---',
                      '_' if can else 'd')
            scr.rtext(55, y, f'${price:,}' if price else '', 'g' if can else 'd')
            lbl = '[ CONFIRM ]' if (on and self.confirm) else '[ UPGRADE ]'
            if price is None:
                lbl = '[  MAX   ]'
            scr.text(60, y, lbl, 'w' if on else ('_' if can else 'd'),
                     'S' if on else None)
        scr.text(3, 12, 'more capacity means more offers on the apron each '
                 'rotation', 'd')
        sfg = 'g' if p.standing >= 65 else ('a' if p.standing < 40 else '_')
        scr.text(3, 14, f'STANDING {p.standing}', sfg)
        scr.text(3, 15, 'standing gates priority contracts; misses and '
                 'abandonments bleed it', 'd')
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'W/S CHOOSE   SPACE UPGRADE (twice to confirm)   Q BACK', 'c')
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
            if price is None or game.credits < price or game.in_arrears:
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
    SECTIONS = ['fleet', 'refit', 'market', 'buoys']

    def __init__(self, mapview, routeview):
        self.mv, self.rv = mapview, routeview
        self.sec = 'fleet'
        self.frow = self.rrow = self.mrow = self.brow = 0
        self.confirm = False

    def draw(self, scr, game):
        yard = game.shipyard()
        header(scr, game, 'SHIPYARD', 'FLEET & TENDER')
        scr.text(40, 0, f'berths {len(yard.ferries)}/{yard.cap("docks")}', 'c')
        if not game.ships:
            scr.rect(0, 2, scr.cols, 8, 'c', title='FLEET')
            scr.ctext(scr.cols // 2, 5, 'NO HULLS IN SERVICE', 'a')
            self._market(scr, game, yard, 12)
            scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
            scr.text(2, scr.rows - 2, 'W/S CHOOSE   SPACE BUY   Q BACK', 'c')
            eventline(scr, game)
            return

        # ---- fleet -------------------------------------------------------
        scr.rect(0, 2, 44, 10, 'c', title='FLEET')
        scr.text(2, 4, 'HULL', 'c'); scr.text(16, 4, 'ENG RDR HUL', 'c')
        scr.rtext(41, 4, 'STATUS', 'c')
        scr.hline(2, 5, 40, '─', 'd')
        for i, f in enumerate(game.ships[:4]):
            y = 6 + i
            st, sfg = ship_status(f, game)
            on = (self.sec == 'fleet' and i == self.frow)
            scr.text(2, y, '×' if f.derelict else '►', 'm' if f.derelict else 'g')
            scr.text(4, y, f.name, 'w' if on else ('m' if f.derelict else '_'),
                     'S' if on else None)
            scr.text(16, y, ' '.join(f'{f.components[c]:3d}' for c in COMPONENTS),
                     '_')
            scr.rtext(41, y, st[:14], sfg)

        f = game.ships[self.frow % len(game.ships)]
        here = f.port is yard

        # ---- plan --------------------------------------------------------
        scr.rect(44, 2, 15, 21, 'c', title='PLAN')
        art.draw_plan(scr, 47, 4, f, cols=9, rows=17)

        # ---- selected stats ---------------------------------------------
        scr.rect(59, 2, scr.cols - 59, 10, 'c', title='SELECTED')
        stats = [('HULL', f'M/V {f.name}', 'C'), ('CLASS', f.cls, '_'),
                 ('HOLD', f'{f.hold_cap()} slots', '_'),
                 ('SPEED', f'{f.speed():.1f} kts / {f.speed_pt():.1f} NM per tick', '_'),
                 ('EFFICIENCY', f'${f.eff()} / NM', 'a'),
                 ('STATUS', 'DERELICT' if f.derelict else
                  ('IN YARD' if here else 'NOT HERE'),
                  'm' if f.derelict else ('g' if here else 'a'))]
        for i, (kk, v, fg) in enumerate(stats):
            scr.text(61, 4 + i, kk, 'c')
            scr.rtext(scr.cols - 3, 4 + i, v, fg)

        # ---- refit -------------------------------------------------------
        scr.rect(0, 12, 44, 11, 'c', title=f'REFIT  M/V {f.name}')
        rows = []
        for kk, label, unit in (('hold', 'Hold', ' slots'), ('spd', 'Speed', ' kts'),
                                ('eff', 'Efficiency', ' $/NM')):
            arr = CLASSES[f.cls][kk]
            lv = f.lv[kk]
            nxt = arr[lv + 1] if lv < len(arr) - 1 else None
            rows.append((label + unit, arr[lv], nxt, f.upgrade_price(kk),
                         lv, len(arr)))
        self._refit_table(scr, 2, 14, rows, game, here and not f.derelict)
        if f.derelict:
            scr.text(2, 21, 'derelict: repair her hull before anything else', 'm')
        elif not here:
            scr.text(2, 21, 'sail her to the yard to refit', 'a')

        # ---- market + buoys ---------------------------------------------
        self._market(scr, game, yard, 12)
        self._buoys(scr, game, 23)

        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'TAB SECTION   W/S CHOOSE   SPACE ACT (twice confirms)   '
                 'R REPAIR   RETURN ROUTE   Q BACK', 'c')
        scr.rtext(scr.cols - 2, scr.rows - 2, self.sec.upper() + ' <', 'w')
        eventline(scr, game)

    def _market(self, scr, game, yard, top):
        x = 59 if game.ships else 0
        w = scr.cols - x
        scr.rect(x, top, w, 11, 'c', title='NEW HULLS')
        scr.text(x + 2, top + 2, 'CLASS', 'c')
        scr.rtext(x + 17, top + 2, 'HOLD', 'c'); scr.rtext(x + 25, top + 2, 'KTS', 'c')
        scr.rtext(x + 33, top + 2, '$/NM', 'c'); scr.rtext(x + 43, top + 2, 'PRICE', 'c')
        berth = yard.berths_free(game) > 0
        for i, (name, spec) in enumerate(CLASSES.items()):
            y = top + 3 + i
            can = game.credits >= spec['price'] and berth and not game.in_arrears
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
        note = 'berth required to take delivery' if not berth else \
            ('accounts in arrears -- clear them first' if game.in_arrears
             else 'delivered to a free berth here')
        scr.text(x + 2, top + 8, note,
                 'a' if (not berth or game.in_arrears) else 'd')

    def _buoys(self, scr, game, top):
        x, w = 0, 59
        scr.rect(x, top, w, 7, 'c', title='BUOY TENDER')
        dark = [n for n in routes.NODES
                if n not in routes.PORTS and n not in game.buoys]
        if not dark:
            scr.text(x + 2, top + 2, 'every station on the chart is lit', 'g')
        for i, nid in enumerate(dark[:4]):
            y = top + 2 + i
            pos = routes.NODES[nid]
            near = min(game.ports, key=lambda p: world.dist(p.pos, pos))
            on = (self.sec == 'buoys' and i == self.brow)
            can = game.credits >= BUOY_PRICE and not game.in_arrears
            lbl = f'STATION {nid}'
            if on and self.confirm and can:
                lbl += '  CONFIRM?'
            scr.text(x + 2, y, lbl, 'w' if on else ('_' if can else 'd'),
                     'S' if on else None)
            scr.text(x + 22, y, f'{world.dist(near.pos, pos):4.1f} NM off '
                     f'{near.code}', 'd')
            scr.rtext(x + 46, y, f'${BUOY_PRICE:,}', 'g' if can else 'd')
            scr.rtext(x + 56, y, f'+${BUOY_UPKEEP}/t', 'a')
        return dark

    def _refit_table(self, scr, x, y, rows, game, workable):
        for i, (name, curv, nxt, price, lv, mx) in enumerate(rows):
            yy = y + 1 + i * 2
            can = workable and price is not None and game.credits >= price \
                and not game.in_arrears
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
        yard = game.shipyard()
        if not game.ships:
            self.sec = 'market'
            if k == pg.K_q:
                return 'map'
            if k in (pg.K_w, pg.K_s):
                self.mrow = (self.mrow + (1 if k == pg.K_s else -1)) % len(CLASSES)
                self.confirm = False
            elif k == pg.K_SPACE:
                self._buy(game, yard)
            return 'shipyard'
        f = game.ships[self.frow % len(game.ships)]
        here = f.port is yard
        if k == pg.K_q:
            return 'map'
        if k == pg.K_r:
            if here:
                self.mv.sel = game.ports.index(yard)
                return 'repair'
            game.log(f'{f.name} is not in a berth here', 'a')
            return 'shipyard'
        if k == pg.K_RETURN:
            if here and not f.derelict:
                self.mv.sel_ship = game.ships.index(f)
                self.rv.back = 'shipyard'
                return 'route'
            game.log(f'{f.name} cannot take a route order', 'a')
            return 'shipyard'
        if k == pg.K_TAB:
            order = self.SECTIONS
            self.sec = order[(order.index(self.sec) + 1) % len(order)]
            self.confirm = False
        elif k in (pg.K_w, pg.K_s):
            d = 1 if k == pg.K_s else -1
            if self.sec == 'fleet':
                self.frow = (self.frow + d) % len(game.ships)
            elif self.sec == 'refit':
                self.rrow = (self.rrow + d) % 3
            elif self.sec == 'market':
                self.mrow = (self.mrow + d) % len(CLASSES)
            else:
                dark = [n for n in routes.NODES if n not in routes.PORTS
                        and n not in game.buoys]
                if dark:
                    self.brow = (self.brow + d) % min(4, len(dark))
            self.confirm = False
        elif k == pg.K_SPACE:
            if self.sec == 'refit':
                kind = ['hold', 'spd', 'eff'][self.rrow]
                price = f.upgrade_price(kind)
                if not here or f.derelict or price is None \
                        or game.credits < price or game.in_arrears:
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
            elif self.sec == 'buoys':
                dark = [n for n in routes.NODES if n not in routes.PORTS
                        and n not in game.buoys]
                if not dark:
                    return 'shipyard'
                nid = dark[self.brow % min(4, len(dark))]
                if not self.confirm:
                    self.confirm = True
                elif game.buy_buoy(nid):
                    self.confirm = False
                else:
                    self.confirm = False
        return 'shipyard'

    def _buy(self, game, yard):
        name = list(CLASSES)[self.mrow]
        spec = CLASSES[name]
        if game.credits < spec['price'] or yard.berths_free(game) <= 0 \
                or game.in_arrears:
            self.confirm = False
            return
        if not self.confirm:
            self.confirm = True
            return
        import sim
        pool = ['RESOLUTE', 'TEMPEST', 'AURORA', 'CORMORANT', 'VIGIL',
                'HALCYON', 'MERIDIAN', 'SENTINEL', 'PILGRIM', 'BEACON']
        taken = {f.name for f in game.ships}
        free = [n for n in pool if n not in taken]
        nm = game.rng.choice(free) if free else f'HULL-{len(game.ships) + 1}'
        game.ships.append(sim.Ship(nm, name, yard))
        game.credits -= spec['price']
        game.log(f'M/V {nm} ({name}) delivered, -${spec["price"]:,}')
        self.confirm = False


# ================================================================== in-hull
class InHullView:
    """The ship's instruments. Same alphabet, zoomed to the sensor envelope.
    No cameras. Beyond sensor range the screen is not black -- it is absent.

    Radar: a directional sweep, crisp, short decay, blocked by land.
    Sonar: always on, omnidirectional, bearings smeared, never a range.
    Ping: everything at once, and everything knows where you are.
    The two instruments do not agree about the thing in the basin.
    """
    SWEEP_DPS = 110.0            # sweep degrees per wall-second
    FADE_S = 7.0                 # radar return afterglow
    CX, CY = 31, 16              # scope center cell
    SW, SH = 62, 28              # scope extent in cells

    def __init__(self, mapview):
        self.mv = mapview
        self.ship_name = None
        self.sweep = 0.0
        self.rays = {}               # deg -> (stamp, [(wx, wy)] land points)
        self.fixes = {}              # name -> (stamp, wx, wy)
        self.afix = None             # (stamp, wx, wy) radar's anomaly claim
        self.flash_until = -9.0      # ping flash window
        self._last_anim = None

    def ship(self, game):
        return self.mv.ship(game)

    # ---- geometry --------------------------------------------------------
    def _scales(self, scr, f):
        r = max(2.5, f.radar_r())
        sy = r / (self.SH / 2 - 1)
        sx = sy * (scr.cw / scr.ch) if scr else sy * 0.5
        return sx, sy, r

    def to_cell(self, scr, f, wx, wy):
        sx, sy, _ = self._scales(scr, f)
        return (self.CX + int(round((wx - f.pos[0]) / sx)),
                self.CY + int(round((wy - f.pos[1]) / sy)))

    # ---- sensor model ----------------------------------------------------
    def _anomaly_radar_pos(self, game):
        """Where radar *claims* the anomaly is: bearing rotated a few
        degrees about the hull. Sonar disagrees the other way."""
        f = self.ship(game)
        ax, ay = game.anomaly.pos
        jit = math.radians(8 + (game.tick_no * 7) % 5)
        dx, dy = ax - f.pos[0], ay - f.pos[1]
        c, s = math.cos(jit), math.sin(jit)
        return (f.pos[0] + dx * c - dy * s, f.pos[1] + dx * s + dy * c)

    def _cast(self, game, f, deg, now):
        """March one bearing out to the envelope; land shadows the rest."""
        th = math.radians(deg)
        dx, dy = math.cos(th), math.sin(th)
        pts, step = [], 0.35
        n = int(f.radar_r() / step)
        for i in range(1, n + 1):
            wx, wy = f.pos[0] + dx * step * i, f.pos[1] + dy * step * i
            if world.land(wx, wy):
                pts.append((wx, wy))
                nx, ny = wx + dx * step, wy + dy * step
                if world.land(nx, ny):
                    pts.append((nx, ny))
                break
            for g in game.ships:
                if g is not f and world.dist((wx, wy), g.pos) < 0.6:
                    self.fixes[g.name] = (now, g.pos[0], g.pos[1])
            if game.anomaly.alive:
                rp = self._anomaly_radar_pos(game)
                if world.dist((wx, wy), rp) < 0.8:
                    self.afix = (now, rp[0], rp[1])
        self.rays[deg] = (now, pts)

    def _update(self, game, now):
        f = self.ship(game)
        if self._last_anim is None or f.name != self.ship_name:
            self._last_anim = now
            self.ship_name = f.name
            self.rays.clear(); self.fixes.clear(); self.afix = None
        dt = min(0.5, max(0.0, now - self._last_anim))
        self._last_anim = now
        if f.components['RDR'] <= 0:
            return                       # a dead array sweeps nothing
        start = int(self.sweep)
        self.sweep = (self.sweep + self.SWEEP_DPS * dt) % 360.0
        end = int(self.sweep)
        deg, guard = start, 0
        while deg != end and guard < 361:
            deg = (deg + 1) % 360
            guard += 1
            self._cast(game, f, deg, now)

    def ping(self, game, now):
        f = self.ship(game)
        game.ping(f)
        for d in range(360):
            self._cast(game, f, d, now)
        self.flash_until = now + 2.5

    # ---- draw ------------------------------------------------------------
    def draw(self, scr, game):
        f = self.ship(game)
        now = self.mv.anim
        header(scr, game, 'IN-HULL', f'M/V {f.name}' if f else '')
        if f is None:
            scr.ctext(scr.cols // 2, 12, 'NO HULL SELECTED', 'd')
            eventline(scr, game)
            return
        if f.derelict:
            scr.ctext(self.CX, 14, 'ALL SYSTEMS DARK', 'm')
            scr.ctext(self.CX, 16, 'she is not listening to anyone', 'd')
            self._panels(scr, game, f, now)
            eventline(scr, game)
            return
        self._update(game, now)
        sx, sy, r = self._scales(scr, f)

        # range rings -- the only soft geometry on the boat
        ring_nm = 2.0
        while ring_nm <= r + 0.01:
            for d in range(0, 360, 4):
                th = math.radians(d)
                x = self.CX + int(round(math.cos(th) * ring_nm / sx))
                y = self.CY + int(round(math.sin(th) * ring_nm / sy))
                self._put(scr, x, y, '·', 'D')
            ring_nm += 2.0

        # sonar: smeared bearings, no ranges, long patience ---------------
        for g in game.ships:
            if g is f or g.port is not None or g.derelict:
                continue
            b = math.atan2(g.pos[1] - f.pos[1], g.pos[0] - f.pos[0])
            b += math.sin(now * 0.7 + hash(g.name) % 7) * 0.10
            self._bearing_line(scr, b, sx, sy, r, 'd')
        if game.anomaly.alive:
            ax, ay = game.anomaly.pos
            if world.dist(f.pos, (ax, ay)) < r * 2.5:
                b = math.atan2(ay - f.pos[1], ax - f.pos[0])
                b -= math.radians(8) + math.sin(now * 0.9) * 0.06
                self._bearing_line(scr, b, sx, sy, r, 'm')

        # radar returns with afterglow ------------------------------------
        for deg, (stamp, pts) in self.rays.items():
            age = now - stamp
            if age > self.FADE_S:
                continue
            fg = 'R' if age < 1.2 else ('c' if age < 3.5 else 'd')
            for wx, wy in pts:
                x, y = self.to_cell(scr, f, wx, wy)
                self._put(scr, x, y, '█' if age < 3.5 else '▓', fg)

        # the sweep line itself -------------------------------------------
        th = math.radians(self.sweep)
        d_nm, step_nm = 0.6, 0.3
        while d_nm <= r:
            x = self.CX + int(round(math.cos(th) * d_nm / sx))
            y = self.CY + int(round(math.sin(th) * d_nm / sy))
            self._put(scr, x, y, '·', 'C')
            d_nm += step_nm

        # contacts the sweep has fixed ------------------------------------
        for name, (stamp, wx, wy) in self.fixes.items():
            age = now - stamp
            if age > self.FADE_S:
                continue
            g = game.ship(name)
            x, y = self.to_cell(scr, f, wx, wy)
            self._put(scr, x, y, '×' if (g and g.derelict) else '►',
                      'm' if (g and g.derelict) else ('w' if age < 1.2 else 'g'))
            if age < 3.5:
                self._text(scr, x + 2, y, name, 'd')

        # the disputed return ---------------------------------------------
        if self.afix and now - self.afix[0] <= self.FADE_S:
            x, y = self.to_cell(scr, f, self.afix[1], self.afix[2])
            self._put(scr, x, y, '?', 'm')
            if now - self.afix[0] < 3.5:
                self._text(scr, x + 2, y, 'DISPUTED', 'm')
        if now < self.flash_until and game.anomaly.alive:
            ax, ay = game.anomaly.pos
            if world.dist(f.pos, (ax, ay)) <= r:
                x, y = self.to_cell(scr, f, ax, ay)
                self._put(scr, x, y, '?', 'w')
                self._text(scr, x + 2, y, 'RESOLVED (fading)', 'w')

        # own hull ---------------------------------------------------------
        hx, hy = f.heading
        g = '►' if abs(hx) >= abs(hy) and hx >= 0 else \
            '◄' if abs(hx) >= abs(hy) else ('▼' if hy > 0 else '▲')
        self._put(scr, self.CX, self.CY, g, 'w')

        self._panels(scr, game, f, now)
        scr.hline(0, scr.rows - 3, scr.cols, '═', 'c')
        scr.text(2, scr.rows - 2,
                 'P PING   TAB NEXT HULL   SPACE TICK   RETURN RUN   Q BACK', 'c')
        eventline(scr, game)

    def _panels(self, scr, game, f, now):
        PX = 64
        scr.vline(PX - 1, 2, scr.rows - 5, '║', 'c')
        scr.rect(PX, 2, scr.cols - PX, 8, 'c', title='SENSORS')
        rows = [('RADAR', f'{f.radar_r():.1f} NM sweep',
                 'g' if f.components['RDR'] > 60 else 'a'),
                ('ARRAY', f"RDR {f.components['RDR']}",
                 'g' if f.components['RDR'] > 60 else
                 ('a' if f.components['RDR'] > 0 else 'm')),
                ('SONAR', 'PASSIVE / OMNI', 'g'),
                ('WATER', f'STABILITY {game.stability(*f.pos, exclude=f)}/4'
                 + (' +1 radar' if f.components['RDR'] >= 30 else ''), '_'),
                ('FLAG', 'OBSERVED' if game.observed is f else 'unheld',
                 'g' if game.observed is f else 'd')]
        for i, (k, v, fg) in enumerate(rows):
            scr.text(PX + 2, 4 + i, k, 'c')
            scr.rtext(scr.cols - 3, 4 + i, v, fg)

        scr.rect(PX, 10, scr.cols - PX, 7, 'c', title='EMISSIONS')
        n = f.noise
        bar = '[' + '#' * (n // 10) + '.' * (10 - n // 10) + ']'
        nfg = 'g' if n < 15 else ('a' if n < 40 else 'm')
        scr.text(PX + 2, 12, 'NOISE', 'c')
        scr.rtext(scr.cols - 3, 12, f'{n:3d} {bar}', nfg)
        scr.text(PX + 2, 13, 'ENGINE', 'c')
        scr.rtext(scr.cols - 3, 13, '+2 / tick underway', 'd')
        scr.text(PX + 2, 14, 'PING', 'c')
        scr.rtext(scr.cols - 3, 14, '+30, full resolution', 'd')
        scr.text(PX + 2, 15, 'every act of looking announces', 'd')

        scr.rect(PX, 17, scr.cols - PX, 9, 'c', title='CONTACTS')
        y = 19
        for name, (stamp, wx, wy) in sorted(self.fixes.items()):
            if now - stamp > self.FADE_S or y > 23:
                continue
            scr.text(PX + 2, y, name[:12], '_')
            scr.rtext(scr.cols - 3, y,
                      f'brg {bearing(f.pos, (wx, wy)):03d}  '
                      f'{world.dist(f.pos, (wx, wy)):4.1f} NM', '_')
            y += 1
        if game.anomaly.alive:
            ax, ay = game.anomaly.pos
            if world.dist(f.pos, (ax, ay)) < f.radar_r() * 2.5 and y <= 23:
                scr.text(PX + 2, y, 'DISPUTED', 'm')
                scr.rtext(scr.cols - 3, y, 'rng unknown', 'm')
                scr.text(PX + 4, y + 1, 'radar/sonar disagree', 'm')
                y += 2
        if y == 19:
            scr.text(PX + 2, 19, 'no returns on the plot', 'd')

        st, sfg = ship_status(f, game)
        scr.text(PX + 2, scr.rows - 6, st, sfg)

    def _bearing_line(self, scr, th, sx, sy, r, fg):
        d_nm = 1.2
        while d_nm <= r:
            k = int(d_nm / 0.4)
            if k % 3 != 0:               # dashed: a guess, not a fact
                x = self.CX + int(round(math.cos(th) * d_nm / sx))
                y = self.CY + int(round(math.sin(th) * d_nm / sy))
                self._put(scr, x, y, '∙', fg)
            d_nm += 0.4

    def _put(self, scr, x, y, ch, fg):
        if 0 <= x < self.SW and 2 <= y < 2 + self.SH:
            scr.put(x, y, ch, fg)

    def _text(self, scr, x, y, s, fg):
        for i, ch in enumerate(s):
            self._put(scr, x + i, y, ch, fg)

    def key(self, k, game):
        f = self.ship(game)
        if k == pg.K_q:
            return 'map'
        if k == pg.K_TAB and game.ships:
            self.mv.sel_ship = (self.mv.sel_ship + 1) % len(game.ships)
            return 'inhull'
        if k == pg.K_p and f and not f.derelict:
            self.ping(game, self.mv.anim)
        elif k == pg.K_SPACE:
            return 'tick'
        elif k == pg.K_RETURN:
            return 'run'
        return 'inhull'
