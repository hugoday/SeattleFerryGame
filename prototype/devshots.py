"""Headless screenshot harness -- renders every view to PNG for inspection."""
import os
import sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame as pg  # noqa: E402

pg.init()
pg.display.set_mode((1, 1))

from screen import Screen  # noqa: E402
from sim import Game       # noqa: E402
import ui                  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

scr = Screen(cols=106, rows=33, fontpx=32)
surface = pg.Surface(scr.px)

game = Game()
# stage some state: load a ferry, send another to sea, wake the anomaly
p0 = game.ports[0]
f0 = game.ferries[0]
for c in list(p0.cargo[:3]):
    p0.cargo.remove(c)
    f0.cargo.append(c)
if p0.cargo:
    p0.stage.append(p0.cargo.pop())
game.ferries[1].depart(game.ports[2], game)
for _ in range(60):
    game.tick(0.5)

mv = ui.MapView()
cv = ui.CargoView(mv)
dv = ui.DestView(mv, cv)
views = {'map': ('navy', mv), 'cargo': ('dark', cv),
         'destination': ('dark', dv),
         'shipyard': ('dark', ui.ShipyardView(mv, dv)),
         'portupgrade': ('dark', ui.PortUpgradeView(mv))}

for name, (theme, view) in views.items():
    scr.begin(theme)
    view.draw(scr, game)
    scr.flush(surface)
    path = os.path.join(OUT, f'proto_{name}.png')
    pg.image.save(surface, path)
    print(path)

# a zoomed map too
mv.scale_i = 1
mv.cx, mv.cy = 56, 17
scr.begin('navy')
mv.draw(scr, game)
scr.flush(surface)
pg.image.save(surface, os.path.join(OUT, 'proto_map_regional.png'))
print(os.path.join(OUT, 'proto_map_regional.png'))
print('OK')
