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
    self.screen.blit(text, text.get_rect(centerx=1920 / 2, y=400))

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

  def draw(self):
    self.screen.blit(self.title, self.title.get_rect(centerx=1920 / 2, y=200))
    self.screen.blit(self.startButton, self.startButton.get_rect(centerx=1920 / 3, y=400))
    self.screen.blit(self.quitButton, self.quitButton.get_rect(centerx=1920 / 3 * 2, y=400))
    if self.selection == "start":
      self.screen.blit(self.selector, self.selector.get_rect(centerx=1920 / 3, y=400))
    else:
      self.screen.blit(self.selector, self.selector.get_rect(centerx=1920 / 3 * 2, y=400))

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
    self.credits = 1000

  def draw(self):
    self.creditSprite = self.font.render("$"+str(self.credits), True, (0, 255, 0))
    self.screen.blit(self.creditSprite, (10, 10))

class CargoSelect(UiElement):
  def __init__(self):
    log("New CargoSelect")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.columns = [self.font.render(item, True, (255, 255, 255))\
                    for item in ["Destination", "Contents", "Payment", "Load/Unload"]]
    self.selection = 2 # 0 = close, 1 = next

  def draw(self, port: Port, ferry: Ferry):
    colSpacing = [600, 800, 1000, 1200]
    title = self.font.render(port.name, True, (255, 255, 255))
    close = self.font.render("[  Close  ]", True, (255, 255, 255), (97,165,194) if self.selection == 0 else (1,42,74))
    next  = self.font.render("[  ---->  ]", True, (255, 255, 255) if ferry else (150,150,150), \
                             (97,165,194) if self.selection == 1 else (1,42,74))
    
    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=400))
    self.screen.blit(next,   next.get_rect(centerx=1920 / 5 * 4, y=400))
    for col, attribute in enumerate(self.columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    # blit cargo
    # gather port and current ferry cargo, sort
    cargo = []
    cargo.extend(port.cargo)
    cargo.extend(ferry.cargo if ferry else [])
    cargo.sort(key=lambda item: item.destination.name + str(item))
    for row, item in enumerate(cargo):
      self.screen.blit(self.font.render(item.destination.name, True, (255, 255, 255)), ((colSpacing[0], 20*row+70)))
      self.screen.blit(self.font.render(item.contents,         True, (255, 255, 255)), ((colSpacing[1], 20*row+70)))
      self.screen.blit(self.font.render(f"${item.payment:>6}", True, (255, 255, 255)), ((colSpacing[2], 20*row+70)))

      # load button logic
      loadText       = "[ UNLOAD ]"  if ferry and item in ferry.cargo else "[  LOAD  ]"
      loadColor      = (150,150,150) if not ferry or (item not in ferry.cargo and len(ferry.cargo) == ferry.capacity) else (255,255,255)
      loadBackground = (97,165,194) if self.selection-2 == row else (1,42,74)
      text = self.font.render(loadText, True, loadColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[3] + self.columns[3].get_width()/2, y=20*row+70))

    # blit loaded graphic
    if ferry: self.drawFerryLoadingCapacity(ferry)

  def processKeypress(self, key, port: Port, ferry: Ferry):
    cargo = []
    cargo.extend(port.cargo)
    cargo.extend(ferry.cargo if ferry else [])
    match(key):
      case(pg.K_a):
        if   self.selection == 1:
          if cargo: self.selection = 2
          else:     self.selection = 0
        elif self.selection >= 2: self.selection = 0

      case(pg.K_d):
        if   self.selection == 0:
          if cargo: self.selection = 2
          else:     self.selection = 1
        elif self.selection >= 2: self.selection = 1

      case(pg.K_w):
        if   self.selection in [0, 1]:  self.selection = len(cargo) + 1
        elif self.selection > 2:        self.selection -= 1

      case(pg.K_s):
        if   self.selection == len(cargo) + 1:  self.selection = 1
        elif self.selection >= 2: self.selection += 1

      case(pg.K_SPACE):
        if self.selection == 0:
          return "game"
        elif self.selection == 1 and ferry:
          return "destMenu"
        elif ferry:
          # if loaded, unload
          cargo.sort(key=lambda item: item.destination.name + str(item))
          if cargo[self.selection-2] in ferry.cargo:
            ferry.cargo.remove(cargo[self.selection-2])
            port.cargo.append(cargo[self.selection-2])
          # not loaded, check if there is space and load
          elif len(ferry.cargo) < ferry.capacity:
            ferry.cargo.append(cargo[self.selection-2])
            port.cargo.remove(cargo[self.selection-2])
    return "cargoMenu"

class DestinationSelect(UiElement):
  def __init__(self):
    log("New DestinationSelect")
    pg.sprite.Sprite.__init__(self)
    # internal objects
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.title = self.font.render("Select destination:", True, (255, 255, 255))
    self.columns = [self.font.render(item, True, (255, 255, 255))\
                    for item in ["Destination", "Cargo", "Bonus", "Profit"]]
    self.selection = 2 # 0 = close, 1 = next

  def draw(self, port: Port, ferry: Ferry):
    colSpacing = [600, 850, 1100, 1200]
    close  = self.font.render("[   Back   ]", True, (255, 255, 255), (97,165,194) if self.selection == 0 else (1,42,74))
    next   = self.font.render("[  Depart  ]", True, (255, 255, 255), (97,165,194) if self.selection == 1 else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(self.title, self.title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=400))
    self.screen.blit(next, next.get_rect(centerx=1920 / 5 * 4, y=400))

    # draw column headers
    for col, attribute in enumerate(self.columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    # blit ports
    for row, port in enumerate(port.destinations):
      destination = self.font.render(f"[{port.name:^20}]", True, \
                              (  0,255,  0) if ferry.destination == port else (255,255,255), \
                              ( 97,165,194) if self.selection-2  == row  else (1,42,74))
      self.screen.blit(destination, ((colSpacing[0], 20*row+70)))

      destItems = [item for item in ferry.cargo if item.destination == port]

      bonus = f"{5 * (len(destItems)-1):>2}%" if destItems else ""
      profit = ((len(destItems)-1)*0.05 + 1) * sum(item.payment for item in destItems)

      self.screen.blit(self.font.render("[X]" * len(destItems), True, (255, 255, 255)), ((colSpacing[1], 20*row+70)))
      self.screen.blit(self.font.render(bonus,                  True, (255, 255, 255)), ((colSpacing[2], 20*row+70)))
      self.screen.blit(self.font.render(f"${profit:>6.0f}",     True, (255, 255, 255)), ((colSpacing[3], 20*row+70)))

    # blit loaded graphic
    self.drawFerryLoadingCapacity(ferry)

  def processKeypress(self, key, port: Port, ferry: Ferry):
    match(key):
      case(pg.K_a):
        if   self.selection == 1: self.selection = 2
        elif self.selection >= 2: self.selection = 0

      case(pg.K_d):
        if   self.selection == 0: self.selection = 2
        elif self.selection >= 2: self.selection = 1

      case(pg.K_w):
        if   self.selection in [0, 1]:  self.selection = len(port.destinations) + 1
        elif self.selection > 2:        self.selection -= 1

      case(pg.K_s):
        if   self.selection == len(port.destinations) + 1:  self.selection = 1
        elif self.selection >= 2:                           self.selection += 1

      case(pg.K_SPACE):
        if self.selection == 0:
          return "cargoMenu"
        elif self.selection == 1:
          # check that a destination is selected
          if not ferry.destination:
            return "destMenu"
          port.ferries.remove(ferry)
          # launch ferry
          ferry.distanceFromDest = 5
          ferry.depart()
          return "game"
        else:
          ferry.destination = port.destinations[self.selection-2]

    return "destMenu"

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

  def draw(self):
    # draw landscape
    self.screen.blit(self.landscape.sprite, (0,0))
    # for island in self.islands:
    #   self.screen.blit(island.sprite, island.pos)
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

  def processKeypress(self, key):
    match(key):
      case(pg.K_a):
        self.selection = self.ports[(self.ports.index(self.selection) - 1) % len(self.ports)]

      case(pg.K_d):
        self.selection = self.ports[(self.ports.index(self.selection) + 1) % len(self.ports)]

      # case(pg.K_w):

      # case(pg.K_s):

      case(pg.K_SPACE):
        return "cargoMenu"
    return "game"
