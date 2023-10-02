from .GameElements import *
from logger import log
from assets.assets import UiAssets
from data.data import *
from .StaticElements import *
from .MovingElements import *

class UiElement(GameElement):
  def __init__(self):
    log("New UiElement")
    self.font = pg.font.SysFont("consolas", 24)
    self.screen = pg.display.get_surface()
    
  def drawFerryLoadingCapacity(self, ferry: Ferry):
    slotText = "[X]" * len(ferry.cargo) + "[ ]" * (ferry.capacity - len(ferry.cargo))
    text = self.font.render(slotText, True, (255, 255, 255))
    self.screen.blit(text, text.get_rect(centerx=640 / 2, y=400))

class StartMenu(UiElement):
  def __init__(self):
    log("New StartMenu")
    pg.sprite.Sprite.__init__(self)
    self.font = pg.font.SysFont("consolas", 24)
    self.screen = pg.display.get_surface()
    self.selection = "start"
    self.title = self.font.render("Seattle Ferry Inc.", True, (255, 255, 255))
    self.startButton = self.font.render("Start Game", True, (255, 255, 255))
    self.quitButton  = self.font.render("Quit Game", True, (255, 255, 255))
    self.selector    = self.font.render("[           ]", True, (255, 255, 255))

  def draw(self):
    self.screen.blit(self.title, self.title.get_rect(centerx=640 / 2, y=10))
    self.screen.blit(self.startButton, self.startButton.get_rect(centerx=640 / 3, y=200))
    self.screen.blit(self.quitButton, self.quitButton.get_rect(centerx=640 / 3 * 2, y=200))
    if self.selection == "start":
      self.screen.blit(self.selector, self.selector.get_rect(centerx=640 / 3, y=200))
    else:
      self.screen.blit(self.selector, self.selector.get_rect(centerx=640 / 3 * 2, y=200))

  def processKeypress(self, key):
    # menu navigation
    if key == pg.K_a:
      self.selection = "start"
    elif key == pg.K_d:
      self.selection = "quit"
    
    # menu select
    if key == pg.K_SPACE and self.selection == "start":
      return "game"
    elif key == pg.K_SPACE and self.selection == "quit":
      return "quit"
    return "startMenu"
    
class CreditsDisplay(UiElement):
  def __init__(self):
    log("New Credits")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.credits = self.font.render("$"+str(credits), True, (0, 255, 0))

  def draw(self):
    self.screen.blit(self.credits, (10, 10))

class CargoSelect(UiElement):
  def __init__(self):
    log("New CargoSelect")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.title = self.font.render("Select cargo:", True, (255, 255, 255))
    self.columns = [self.font.render(item, True, (255, 255, 255))\
                    for item in ["Destination", "Contents", "Payment", "Load/Unload"]]
    self.colSpacing = [10, 250, 400, 500]
    self.selection = 2 # 0 = close, 1 = next

  def draw(self, port: Port, ferry: Ferry):
    close  = self.font.render("[  Close  ]", True, (255, 255, 255), (0,0,150) if self.selection == 0 else (0,0,0))
    next   = self.font.render("[  ---->  ]", True, (255, 255, 255), (0,0,150) if self.selection == 1 else (0,0,0))
    
    # blit header and menu buttons
    self.screen.blit(self.title, self.title.get_rect(centerx=640 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=640 / 5, y=400))
    self.screen.blit(next, next.get_rect(centerx=640 / 5 * 4, y=400))
    for col, attribute in enumerate(self.columns):
      self.screen.blit(attribute, (self.colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    # blit cargo
    for row, item in enumerate(port.cargo):
      # print item destination
      self.screen.blit(self.font.render(item.destination.name, True, (255, 255, 255)), ((self.colSpacing[0], 20*row+70)))

      # print contents
      self.screen.blit(self.font.render(item.contents, True, (255, 255, 255)), ((self.colSpacing[1], 20*row+70)))

      # print payment
      self.screen.blit(self.font.render(f"${item.payment:>6}", True, (255, 255, 255)), ((self.colSpacing[2], 20*row+70)))

      # load button logic
      loadText       = "[ UNLOAD ]" if item in ferry.cargo else "[  LOAD  ]"
      loadColor      = (150,150,150) if item not in ferry.cargo and len(ferry.cargo) == ferry.capacity else (255,255,255)
      loadBackground = (  0,  0,150) if self.selection-2 == row else ( 0,0,0)
      text = self.font.render(loadText, True, loadColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=self.colSpacing[3] + self.columns[3].get_width()/2, y=20*row+70))

    # blit loaded graphic
    self.drawFerryLoadingCapacity(ferry)

  def processKeypress(self, key, port: Port, ferry: Ferry):
    # menu navigation
        if key == pg.K_a:
          if self.selection == 1:
            self.selection = 0
          elif self.selection >= 2:
            self.selection = 1
        elif key == pg.K_d:
          if self.selection == 0:
            self.selection = 1
          elif self.selection == 1:
            self.selection = 2
        elif key == pg.K_w:
          if self.selection in [0, 1]:
            self.selection = len(port.cargo) + 1
          elif self.selection > 2:
            self.selection -= 1
        elif key == pg.K_s:
          if self.selection == len(port.cargo) + 1:
            self.selection = 1
          elif self.selection >= 2:
            self.selection += 1

        # menu select
        if key == pg.K_SPACE and self.selection == 0:
          return "game"
        elif key == pg.K_SPACE and self.selection == 1:
          return "destMenu"
        elif key == pg.K_SPACE:
          # if loaded, unload
          if port.cargo[self.selection-2] in ferry.cargo:
            ferry.cargo.remove(port.cargo[self.selection-2])
          # not loaded, check if there is space and load
          elif len(ferry.cargo) < ferry.capacity:
            ferry.cargo.append(port.cargo[self.selection-2])
        return "cargoMenu"

class DestinationSelect(UiElement):
  def __init__(self):
    log("New DestinationSelect")
    pg.sprite.Sprite.__init__(self)
    # internal objects
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.title = self.font.render("Select cargo:", True, (255, 255, 255))
    self.columns = [self.font.render(item, True, (255, 255, 255))\
                    for item in ["Destination", "Cargo", "Bonus", "Profit"]]
    self.selection = 2 # 0 = close, 1 = next
    
  def draw(self, port: Port, ferry: Ferry):
    colSpacing = [10, 250, 420, 500]
    close  = self.font.render("[   Back   ]", True, (255, 255, 255), (0,0,150) if self.selection == 0 else (0,0,0))
    next   = self.font.render("[  Depart  ]", True, (255, 255, 255), (0,0,150) if self.selection == 1 else (0,0,0))
    
    # blit header and menu buttons
    self.screen.blit(self.title, self.title.get_rect(centerx=640 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=640 / 5, y=400))
    self.screen.blit(next, next.get_rect(centerx=640 / 5 * 4, y=400))

    # draw column headers
    for col, attribute in enumerate(self.columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    # blit ports
    for row, port in enumerate(port.destinations):
      # port names
      text = self.font.render(f"[{port.name:^20}]", True, \
                              (  0,255,  0) if ferry.destination == port else (255,255,255), \
                              (  0,  0,150) if self.selection-2 == row  else (  0,  0,  0))
      self.screen.blit(text, ((colSpacing[0], 20*row+70)))

      # cargo objects
      destItems = [item for item in ferry.cargo if item.destination.name == port.name]
      text = self.font.render("[X]" * len(destItems), True, (255, 255, 255))
      self.screen.blit(text, ((colSpacing[1], 20*row+70)))

      # bonus amount
      bonusText = f"{5 * (len(destItems)-1):>2}%" if destItems else ""
      self.screen.blit(self.font.render(bonusText, True, (255, 255, 255)), ((colSpacing[2], 20*row+70)))

      # profit
      profit = ((len(destItems)-1)*0.05 + 1) * sum(item.payment for item in destItems)
      self.screen.blit(self.font.render(f"${profit:>6.0f}", True, (255, 255, 255)), ((colSpacing[3], 20*row+70)))

    # blit loaded graphic
    self.drawFerryLoadingCapacity(ferry)

  def processKeypress(self, key, port: Port, ferry: Ferry):
    # menu navigation
        if key == pg.K_a:
          if self.selection == 1:
            self.selection = 0
          elif self.selection == 0:
            self.selection = 2
        elif key == pg.K_d:
          if self.selection == 0:
            self.selection = 1
          elif self.selection >= 2:
            self.selection = 0
        elif key == pg.K_w:
          if self.selection in [0, 1]:
            self.selection = len(port.destinations) + 1
          elif self.selection > 2:
            self.selection -= 1
        elif key == pg.K_s:
          if self.selection == len(port.destinations) + 1:
            self.selection = 0
          elif self.selection >= 2:
            self.selection += 1

        # menu select
        if key == pg.K_SPACE and self.selection == 0:
          return "cargoMenu"
        elif key == pg.K_SPACE and self.selection == 1:
          # check that a destination is selected
          if not ferry.destination:
            return "destMenu"
          # remove cargo from port and add to ferry
          for item in ferry.cargo:
            port.cargo.remove(item)
          # launch ferry
          ferry.distanceFromDest = 5
          ferry.depart()
          return "game"
        elif key == pg.K_SPACE:
          ferry.destination = port.destinations[self.selection-2]
        return "destMenu"


class WorldMap(UiElement):
  def __init__(self):
    log("New WorldMap")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.selection = 0
    self.ports = []
    self.ferries = []

    
  def draw(self):
    # draw landscape

    # draw ports
    for port in self.ports:
      self.screen.blit(port.sprite, port.pos)

    # draw ferries
    for ferry in self.ferries:
      self.screen.blit(ferry.sprite, ferry.pos)

    # draw selector

    