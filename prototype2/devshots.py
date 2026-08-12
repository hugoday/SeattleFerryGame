"""Headless screenshot harness -- renders every view to PNG for inspection.

Stages a state that exercises what the milestone added: a hull mid-leg on
the lane, a derelict in the basin, an anomaly gone stale outside coverage,
damage worth repairing, and a leg-commit panel with real options.
"""
import os
import sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame as pg  # noqa: E402

pg.init()
pg.display.set_mode((1, 1))

from screen import Screen  # noqa: E402
import routes              # noqa: E402
import sim                 # noqa: E402
import ui                  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

scr = Screen(cols=106, rows=33, fontpx=32)
surface = pg.Surface(scr.px)

game = sim.Game(seed=11)
p0, f0, f1 = game.ports[0], game.ships[0], game.ships[1]

# load ENDURANCE and commit her to the lane for Kingston
for c in list(p0.cargo[:3]):
    p0.cargo.remove(c)
    f0.cargo.append(c)
if p0.cargo:
    p0.stage.append(p0.cargo.pop())
opts = routes.options('MER', 'KNG', game.water_for(f0))
f0.enqueue_leg(opts[0], 'KNG', game)
game.set_observed(f0)

# DISCOVERY: wreck her in the southern basin
f1.port.ferries.remove(f1)
f1.port = None
f1.pos = [58.0, 27.0]
f1.components.update(ENG=40, RDR=22, HUL=0)
f1.go_derelict(game, [])

# run until the anomaly has been seen once, then let it go stale
for _ in range(12):
    game.step()
assert game.anomaly.alive, "anomaly should be awake by now"

f0.components['HUL'] = 62          # something worth repairing

mv = ui.MapView()
mv.anim = 3.7
cv = ui.CargoView(mv)
rv = ui.RouteView(mv)
views = {'map': ('navy', mv), 'route': ('dark', rv),
         'cargo': ('dark', cv),
         'repair': ('dark', ui.RepairView(mv, cv)),
         'shipyard': ('dark', ui.ShipyardView(mv, rv)),
         'portupgrade': ('dark', ui.PortUpgradeView(mv))}


def shoot(name, theme, view):
    scr.begin(theme)
    view.draw(scr, game)
    scr.flush(surface)
    path = os.path.join(OUT, f'proto2_{name}.png')
    pg.image.save(surface, path)
    print(path)


# mid-leg states first
for name in ('map', 'route'):
    shoot(name, *views[name])

# let ENDURANCE dock at Kingston, then shoot the port screens there
while f0.port is None:
    game.step()
mv.sel = game.ports.index(f0.port)
for name in ('cargo', 'repair', 'shipyard', 'portupgrade'):
    shoot(name, *views[name])

# regional scale over the basin: derelict, stale contact, shading ramp
mv.scale_i = 1
mv.cx, mv.cy = 58, 24
scr.begin('navy')
mv.draw(scr, game)
scr.flush(surface)
pg.image.save(surface, os.path.join(OUT, 'proto2_map_basin.png'))
print(os.path.join(OUT, 'proto2_map_basin.png'))
print('OK')
