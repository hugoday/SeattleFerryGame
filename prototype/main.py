"""Seattle Ferry Inc. -- text-mode prototype.

Run:  python main.py        (from the prototype directory)
"""
import ctypes
import os
import sys

import pygame as pg

from screen import Screen
import sim
import ui

THEME = {'map': 'navy', 'cargo': 'dark', 'destination': 'dark',
         'shipyard': 'dark', 'portupgrade': 'dark'}


def main():
    if os.name == 'nt':
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    pg.init()
    scr = Screen(cols=106, rows=33, fontpx=32)
    window = pg.display.set_mode(scr.px)
    pg.display.set_caption("Seattle Ferry Inc.")
    pg.key.set_repeat(260, 45)
    clock = pg.time.Clock()

    game = sim.Game()
    mv = ui.MapView()
    cv = ui.CargoView(mv)
    dv = ui.DestView(mv, cv)
    views = {'map': mv, 'cargo': cv, 'destination': dv,
             'shipyard': ui.ShipyardView(mv, dv),
             'portupgrade': ui.PortUpgradeView(mv)}
    state = 'map'

    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                running = False
            elif ev.type == pg.KEYDOWN:
                state = views[state].key(ev.key, game)
                if state == 'quit':
                    running = False
                    state = 'map'
                elif state == 'load':
                    try:
                        game = sim.load()
                    except FileNotFoundError:
                        game.log("no save on disk", 'a')
                    state = 'map'

        game.tick(dt)                       # the world does not pause
        scr.begin(THEME[state])
        views[state].draw(scr, game)
        scr.flush(window)
        pg.display.flip()

    pg.quit()


if __name__ == '__main__':
    main()
