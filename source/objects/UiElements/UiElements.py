from ..GameElements import *
from logger import log
from assets.assets import UiAssets
import data
from ..StaticElements import *
from ..MovingElements import *

class UiElement(GameElement):
  def __init__(self):
    log("New UiElement")
    self.font = pg.font.SysFont("consolas", 24)
    self.screen = pg.display.get_surface()

class Cursor():
  def __init__(self):
    self.section = "option"
    self.selection = "close"
    self.row = 0

  def toSection(self, section, row = 0, selection = None):
    self.section = section
    self.row = row
    if selection: self.selection = selection

  def isSection(self, section):
    if self.section == section: return True
    return False

  def isNext(self):
    if self.selection == "next": return True
    return False

  def toNext(self):
    self.selection = "next"
    self.section = "option"

  def isClose(self):
    if self.selection == "close": return True
    return False

  def toClose(self):
    self.selection = "close"
    self.section = "option"

  def isSelected(self, section = "option", row = 0, selection = "load"):
    if self.section == section and self.row == row and self.selection == selection:
      return True
    return False

class StartMenu(UiElement):
  def __init__(self):
    log("New StartMenu")
    pg.sprite.Sprite.__init__(self)
    self.font = pg.font.SysFont("consolas", 24)
    self.screen = pg.display.get_surface()
    self.selection = "start"
    self.title       = self.font.render("Seattle Ferry Inc.", True, (255, 255, 255))
    self.startButton = self.font.render("Start Game", True, (255, 255, 255))
    self.quitButton  = self.font.render("Quit Game", True, (255, 255, 255))
    self.selector    = self.font.render("[           ]", True, (255, 255, 255))

  def draw(self) -> None:
    self.screen.blit(self.title, self.title.get_rect(centerx=1920 / 2, y=200))
    self.screen.blit(self.startButton, self.startButton.get_rect(centerx=1920 / 3, y=400))
    self.screen.blit(self.quitButton, self.quitButton.get_rect(centerx=1920 / 3 * 2, y=400))
    if self.selection == "start":
      self.screen.blit(self.selector, self.selector.get_rect(centerx=1920 / 3, y=400))
    else:
      self.screen.blit(self.selector, self.selector.get_rect(centerx=1920 / 3 * 2, y=400))

  def processKeypress(self, key) -> str:
    # menu navigation
    if key == pg.K_a:
      self.selection = "start"
    elif key == pg.K_d:
      self.selection = "quit"

    # menu select
    if key == pg.K_SPACE and self.selection == "start":
      return "worldMap"
    elif key == pg.K_SPACE and self.selection == "quit":
      return "quit"
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