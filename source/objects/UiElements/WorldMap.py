from .UiElements import *

class WorldMap(UiElement):
  def __init__(self):
    log("New WorldMap")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.selection = None
    self.ports = []
    self.ferries = []
    # self.islands = []
    self.landscape = Landscape()

  def draw(self) -> None:
    # draw landscape
    self.screen.blit(self.landscape.sprite, (0,0))
    # for island in self.islands:
    #   self.screen.blit(island.sprite, island.pos)

    # draw ports
    for port in self.ports:
      selPort = self.font.render(f"[{port.name:^20}]", True, (255,255,255), \
                                 ( 97,165,194) if self.selection == port else None)
      self.screen.blit(selPort, (port.pos[0], port.pos[1]-20))
      # self.screen.blit(port.sprite, port.pos)

    # draw ferries
    for ferry in self.ferries:
      self.screen.blit(ferry.sprite, ferry.pos)

  def processKeypress(self, key) -> str:
    match(key):
      case(pg.K_a):
        self.selection = self.ports[(self.ports.index(self.selection) - 1) % len(self.ports)]

      case(pg.K_d):
        self.selection = self.ports[(self.ports.index(self.selection) + 1) % len(self.ports)]

      case(pg.K_e):
        return "portUpgrade"

      # case(pg.K_w):

      # case(pg.K_s):

      case(pg.K_SPACE):
        if len(self.selection.ferries) > 1:
          return "ferrySelect"
        return "cargoSelect"
    return "worldMap"