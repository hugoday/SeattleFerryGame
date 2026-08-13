"""Seattle Ferry Inc. -- tick-world prototype.

Run:  python main.py        (from the prototype2 directory)

Time advances only when you spend it: SPACE steps one tick, RETURN runs
until something on the fixed interrupt list happens (arrival, new contact,
damage, derelict, a closing window, a flag dropout). Any key halts a run.
"""
import ctypes
import os

import pygame as pg

from screen import Screen
import sim
import ui

THEME = {'map': 'navy', 'cargo': 'dark', 'route': 'dark', 'repair': 'dark',
         'shipyard': 'dark', 'portupgrade': 'dark', 'inhull': 'dark'}
RUN_TICK_S = 0.22            # real seconds per tick while running


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
    rv = ui.RouteView(mv)
    views = {'map': mv, 'cargo': cv, 'route': rv,
             'repair': ui.RepairView(mv, cv),
             'shipyard': ui.ShipyardView(mv, rv),
             'portupgrade': ui.PortUpgradeView(mv),
             'inhull': ui.InHullView(mv, rv)}
    state = 'map'
    running = True
    auto_run = False
    run_accum = 0.0

    while running:
        dt = clock.tick(30) / 1000.0
        mv.anim += dt                       # flicker is wall-clock, not ticks

        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                running = False
            elif ev.type == pg.KEYDOWN:
                if auto_run:
                    auto_run = False        # any key halts a run
                    continue
                prev = state
                state = views[state].key(ev.key, game)
                if state == 'quit':
                    running = False
                    state = 'map'
                elif state == 'tick':
                    game.step()
                    state = prev
                elif state == 'run':
                    auto_run, run_accum = True, 0.0
                    state = prev
                elif state == 'load':
                    try:
                        game = sim.load()
                    except FileNotFoundError:
                        game.log("no save on disk", 'a')
                    state = 'map'

        if auto_run:
            run_accum += dt
            if run_accum >= RUN_TICK_S:
                run_accum = 0.0
                if game.step():             # an interrupt: hand time back
                    auto_run = False

        scr.begin(THEME[state])
        views[state].draw(scr, game)
        scr.flush(window)
        pg.display.flip()

    pg.quit()


if __name__ == '__main__':
    main()
