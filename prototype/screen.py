"""Cell-buffer renderer. Everything on screen is (glyph, fg, bg) on a grid.

The engine underneath only ever blits glyphs -- all game rendering happens
against this buffer, which keeps the renderer swappable and testable.
"""
import pygame as pg

THEMES = {
    # navy -- the map field. Dim ramp needs a mid-tone behind it.
    'navy': dict(
        bg=(1, 42, 74),
        _=(176, 190, 197), w=(255, 255, 255),
        c=(97, 165, 194), C=(169, 214, 229),
        g=(64, 220, 110), a=(255, 176, 0), m=(233, 84, 233),
        d=(38, 78, 110), D=(22, 55, 82), R=(84, 134, 166),
        S=(20, 62, 96), L=(46, 66, 60), l=(34, 50, 46),
    ),
    # dark -- panel screens. Near-black field, restrained accents.
    'dark': dict(
        bg=(3, 6, 8),
        _=(172, 194, 198), w=(232, 248, 250),
        c=(112, 152, 164), C=(192, 224, 232),
        g=(104, 200, 132), a=(224, 158, 40), m=(224, 78, 186),
        d=(44, 70, 78), D=(26, 42, 48), R=(92, 134, 148),
        S=(34, 60, 70), L=(54, 74, 68), l=(36, 52, 48),
    ),
}


class Screen:
    def __init__(self, cols=106, rows=33, fontpx=32):
        self.font = pg.font.SysFont("consolas", fontpx)
        self.cw, self.ch = self.font.size("M")
        self.cols, self.rows = cols, rows
        self.px = (cols * self.cw, rows * self.ch)
        self.theme = 'dark'
        self._cache = {}
        self.clear()

    # ---------------------------------------------------------- buffer ops
    def clear(self):
        n = self.cols * self.rows
        self.chb = [' '] * n
        self.fgb = ['_'] * n
        self.bgb = [None] * n

    def begin(self, theme):
        if theme != self.theme:
            self.theme = theme
            self._cache.clear()
        self.clear()

    def put(self, x, y, ch, fg='_', bg=None):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            i = y * self.cols + x
            self.chb[i] = ch
            self.fgb[i] = fg
            if bg is not None:
                self.bgb[i] = bg

    def text(self, x, y, s, fg='_', bg=None):
        for i, ch in enumerate(s):
            self.put(x + i, y, ch, fg, bg)

    def rtext(self, x, y, s, fg='_', bg=None):
        self.text(x - len(s) + 1, y, s, fg, bg)

    def ctext(self, cx, y, s, fg='_', bg=None):
        self.text(cx - len(s) // 2, y, s, fg, bg)

    def hline(self, x, y, n, ch='─', fg='_'):
        for i in range(n):
            self.put(x + i, y, ch, fg)

    def vline(self, x, y, n, ch='│', fg='_'):
        for i in range(n):
            self.put(x, y + i, ch, fg)

    def rect(self, x, y, w, h, fg='c', double=True, title=None, tfg='w'):
        a = '╔╗╚╝═║' if double else '┌┐└┘─│'
        self.hline(x + 1, y, w - 2, a[4], fg)
        self.hline(x + 1, y + h - 1, w - 2, a[4], fg)
        self.vline(x, y + 1, h - 2, a[5], fg)
        self.vline(x + w - 1, y + 1, h - 2, a[5], fg)
        self.put(x, y, a[0], fg); self.put(x + w - 1, y, a[1], fg)
        self.put(x, y + h - 1, a[2], fg); self.put(x + w - 1, y + h - 1, a[3], fg)
        if title:
            self.text(x + 2, y, ' ' + title + ' ', tfg)

    # ---------------------------------------------------------- flush
    def _glyph(self, ch, fg):
        key = (ch, fg)
        srf = self._cache.get(key)
        if srf is None:
            color = THEMES[self.theme].get(fg) or THEMES[self.theme]['_']
            srf = self.font.render(ch, False, color)
            self._cache[key] = srf
        return srf

    def flush(self, surface):
        pal = THEMES[self.theme]
        surface.fill(pal['bg'])
        cw, ch = self.cw, self.ch
        i = 0
        for y in range(self.rows):
            yy = y * ch
            for x in range(self.cols):
                bg = self.bgb[i]
                if bg is not None:
                    surface.fill(pal.get(bg, pal['bg']),
                                 (x * cw, yy, cw, ch))
                c = self.chb[i]
                if c != ' ':
                    surface.blit(self._glyph(c, self.fgb[i]), (x * cw, yy))
                i += 1
