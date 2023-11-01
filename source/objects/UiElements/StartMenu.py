from ..GameElements import *
from logger import log
from data.data import *
from data.SaveGame import *
from ..StaticElements import *
from ..MovingElements import *
from .UiElements import *

class StartMenu(UiElement):
  def __init__(self):
    log("New StartMenu")
    pg.sprite.Sprite.__init__(self)
    self.titleFont = pg.font.SysFont("consolas", 24)
    self.font = pg.font.SysFont("consolas", 18)
    self.screen = pg.display.get_surface()
    self.selection = "start"
    self.saveFound = False

  def draw(self, saveFound) -> None:
    self.saveFound = saveFound

    title = self.titleFont.render("Seattle Ferry Inc.", True, (255, 255, 255))
    start = self.font.render("[  Start  ]", True, (255, 255, 255), (97,165,194) if self.selection == "start" else (1,42,74))
    load =  self.font.render("[  Load  ]",  True, (255, 255, 255) if saveFound else (150,150,150), (97,165,194) if self.selection == "load"  else (1,42,74))
    quit =  self.font.render("[  Quit  ]",  True, (255, 255, 255), (97,165,194) if self.selection == "quit"  else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=200))
    self.screen.blit(start, start.get_rect(centerx=1920 / 4 * 1, y=400))
    self.screen.blit(load,   load.get_rect(centerx=1920 / 4 * 2, y=400))
    self.screen.blit(quit,   quit.get_rect(centerx=1920 / 4 * 3, y=400))

  def processKeypress(self, key, worldMap) -> str:
    match(key):
      case(pg.K_a):
        if self.selection == "quit" and self.saveFound:
          self.selection = "load"
        else:
          self.selection = "start"

      case(pg.K_d):
        if self.selection == "start" and self.saveFound:
          self.selection = "load"
        else:
          self.selection = "quit"

      case(pg.K_SPACE):
        if self.selection == "quit": return "quit"
        if self.selection == "start":
          Port.buildPorts()
          Ferry.buildFerries()
        if self.selection == "load":
          SaveGame.loadGame()
        worldMap.selection = GameData.ports[0]
        return "worldMap"
    return "startMenu"

class CreditsDisplay(UiElement):
  def __init__(self):
    log("New Credits")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    # self.credits = 1000

  def draw(self):
    self.creditSprite = self.font.render("$"+str(GameData.credits), True, (0, 255, 0))
    self.screen.blit(self.creditSprite, (10, 10))