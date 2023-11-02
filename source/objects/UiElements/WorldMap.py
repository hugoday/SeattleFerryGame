from .UiElements import *

class WorldMap(UiElement):
  def __init__(self):
    log("New WorldMap")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("islandsMap.png", scale=1)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.selection = None
    self.landscape = Landscape()

  def draw(self) -> None:
    # draw landscape
    self.screen.blit(self.sprite, (0,0))

    # draw ports
    for port in GameData.ports:
      selPort = self.font.render(f"[{port.name:^20}]", True, (255,255,255), \
                                 ( 97,165,194) if self.selection == port else None)
      self.screen.blit(selPort, (port.pos[0], port.pos[1]-20))
      # self.screen.blit(port.sprite, port.pos)

    # draw ferries
    for ferry in GameData.ferries:
      self.screen.blit(ferry.sprite, ferry.pos)

  def processKeypress(self, key) -> str:
    match(key):
      case(pg.K_a):
        self.selection = GameData.ports[(GameData.ports.index(self.selection) - 1) % len(GameData.ports)]

      case(pg.K_d):
        self.selection = GameData.ports[(GameData.ports.index(self.selection) + 1) % len(GameData.ports)]

      case(pg.K_e):
        if self.selection.name != "Shipyard":
          return "portUpgrade"

      # case(pg.K_w):

      # case(pg.K_s):

      case(pg.K_SPACE):
        if len(self.selection.ferries) == 1:
          GameData.uiFerry = self.selection.ferries[0]
        else:
          GameData.uiFerry = None
        if len(self.selection.ferries) > 1:
          return "ferrySelect"
        if self.selection.name == "Shipyard":
          return "ferryUpgrade"
        return "cargoSelect"
    return "worldMap"