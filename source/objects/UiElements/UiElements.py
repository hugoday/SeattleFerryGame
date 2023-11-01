from ..GameElements import *
from logger import log
from ..StaticElements import *
from ..MovingElements import *
from data.data import *

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
