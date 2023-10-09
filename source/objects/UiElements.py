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
    self.credits = 1000

  def draw(self):
    self.creditSprite = self.font.render("$"+str(self.credits), True, (0, 255, 0))
    self.screen.blit(self.creditSprite, (10, 10))

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

class CargoSelect(UiElement):
  def __init__(self):
    log("New CargoSelect")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.cursor = Cursor()

  def draw(self, port: Port, ferry: Ferry):
    cursor = self.cursor
    colSpacing = [600, 800, 1000, 1100, 1220, 1360]
    columns = [self.font.render(item, True, (255, 255, 255))\
                    for item in ["Destination", "Contents", "Payment", "Load/Unload", "Stage/Unstage"]]
    title = self.font.render(port.name, True, (255, 255, 255))
    close = self.font.render("[  Close  ]", True, (255, 255, 255), (97,165,194) if cursor.selection == "close" else (1,42,74))
    next  = self.font.render("[  ---->  ]", True, (255, 255, 255) if ferry else (150,150,150), \
                             (97,165,194) if cursor.selection == "next" else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=1000))
    self.screen.blit(next, next.get_rect(centerx=1920 / 5 * 4, y=1000))
    for col, attribute in enumerate(columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65), (1920-10,65))

    # cargo section
    for row, item in enumerate(sorted(port.cargo, key=lambda item: item.destination.name + str(item))):
      self.screen.blit(item.font.render("[X]", True, (255, 255, 255)), ((colSpacing[0]-40, 20*row+70)))
      self.screen.blit(item.font.render(item.destination.name, True, (255, 255, 255)), ((colSpacing[0], 20*row+70)))
      self.screen.blit(item.font.render(item.contents,         True, (255, 255, 255)), ((colSpacing[1], 20*row+70)))
      self.screen.blit(self.font.render(f"${item.payment:>6}", True, (255, 255, 255)), ((colSpacing[2], 20*row+70)))

      # load button logic
      loadColor = (150,150,150) if not ferry or (item not in ferry.cargo and len(ferry.cargo) == ferry.capacity) \
                                      else (255,255,255)
      loadBackground = (97,165,194) if cursor.isSelected("port", row, "load") else (1,42,74)
      text = self.font.render("[  LOAD  ]", True, loadColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[3] + columns[3].get_width()/2, y=20*row+70))

      stageColor      = (150,150,150) if len(port.stage) == port.stageCapacity else (255,255,255)
      stageBackground = (97,165,194)  if cursor.isSelected("port", row, "stage") else (1,42,74)
      text = self.font.render("[  STAGE  ]", True, stageColor, stageBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[4] + columns[4].get_width()/2, y=20*row+70))
    for row in range(port.cargoCapacity - len(port.cargo)):
      self.screen.blit(item.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0] - 40, 20 * (len(port.cargo) + row) + 70)))

    # stage section
    stageY = 400
    pg.draw.line(self.screen, (255, 255, 255), (10, stageY-5), (1920-10, stageY-5))
    for row, item in enumerate(sorted(port.stage, key=lambda item: item.destination.name + str(item))):
      self.screen.blit(item.font.render("[X]", True, (255, 255, 255)), ((colSpacing[0]-40, 20*row+stageY)))
      self.screen.blit(item.font.render(item.destination.name, True, (255, 255, 255)), ((colSpacing[0], 20*row+stageY)))
      self.screen.blit(item.font.render(item.contents,         True, (255, 255, 255)), ((colSpacing[1], 20*row+stageY)))
      self.screen.blit(self.font.render(f"${item.payment:>6}", True, (255, 255, 255)), ((colSpacing[2], 20*row+stageY)))

      # load button logic
      loadColor = (150,150,150) if not ferry or (item not in ferry.cargo and len(ferry.cargo) == ferry.capacity) \
                                      else (255,255,255)
      loadBackground = (97,165,194) if cursor.isSelected("stage", row, "load") else (1,42,74)
      text = self.font.render("[  LOAD  ]", True, loadColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[3] + columns[3].get_width()/2, y=20*row+stageY))

      stageColor      = (150,150,150) if len(port.cargo) == port.cargoCapacity else (255,255,255)
      stageBackground = (97,165,194)  if cursor.isSelected("stage", row, "stage") else (1,42,74)
      text = self.font.render("[ UNSTAGE ]", True, stageColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[4] + columns[4].get_width()/2, y=20*row+stageY))
    for row in range(port.stageCapacity - len(port.stage)):
      self.screen.blit(item.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0] - 40, 20 * (len(port.stage) + row) + stageY)))

    if not ferry:
      return
    # ferry section
    ferryY = 700
    pg.draw.line(self.screen, (255, 255, 255), (10, ferryY-5), (1920-10, ferryY-5))
    for row, item in enumerate(sorted(ferry.cargo, key=lambda item: item.destination.name + str(item))):
      self.screen.blit(item.font.render("[X]", True, (255, 255, 255)), ((colSpacing[0]-40, 20*row+ferryY)))
      self.screen.blit(item.font.render(item.destination.name, True, (255, 255, 255)), ((colSpacing[0], 20*row+ferryY)))
      self.screen.blit(item.font.render(item.contents,         True, (255, 255, 255)), ((colSpacing[1], 20*row+ferryY)))
      self.screen.blit(self.font.render(f"${item.payment:>6}", True, (255, 255, 255)), ((colSpacing[2], 20*row+ferryY)))

      # load button logic
      loadColor      = (150,150,150) if len(port.cargo) == port.cargoCapacity else (255,255,255)
      loadBackground = (97,165,194)  if cursor.isSelected("ferry", row, "load") else (1,42,74)
      text = self.font.render("[ UNLOAD ]", True, loadColor, loadBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[3] + columns[3].get_width()/2, y=20*row+ferryY))

      stageColor      = (150,150,150) if len(port.stage) == port.stageCapacity else (255,255,255)
      stageBackground = (97,165,194)  if cursor.isSelected("ferry", row, "stage") else (1,42,74)
      text = self.font.render("[  STAGE  ]", True, stageColor, stageBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[4] + columns[4].get_width()/2, y=20*row+ferryY))

      abandonBackground = (97,165,194)  if cursor.isSelected("ferry", row, "abandon") else (1,42,74)
      text = self.font.render("[ ABANDON ]", True, (255,255,255), abandonBackground)
      self.screen.blit(text, (colSpacing[5], 20*row+ferryY))
    for row in range(ferry.capacity - len(ferry.cargo)):
      self.screen.blit(item.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0]-40, 20 * (len(ferry.cargo) + row) + ferryY)))

  def processKeypress(self, key, port: Port, ferry: Ferry):
    cursor = self.cursor
    match(key):
      case(pg.K_a):
        if cursor.isNext(): # next button
          if port.cargo: cursor.toSection("port", 0, "stage") # load option of first port cargo item
          elif port.stage: cursor.toSection("stage", 0, "stage") # load option of first port stage item
          elif ferry and ferry.cargo: cursor.toSection("ferry", 0, "stage") # unload option of first ferry cargo item
          else: cursor.toClose()
        elif cursor.selection == "stage":
          cursor.selection = "load"
        elif cursor.selection == "abandon":
          cursor.selection = "stage"
        else: cursor.toClose()

      case(pg.K_d):
        if cursor.isClose():
          if   port.cargo:  cursor.toSection("port", 0, "load") # load option of first port cargo item
          elif port.stage:  cursor.toSection("stage", 0, "load") # load option of first port stage item
          elif ferry and ferry.cargo: cursor.toSection("ferry", 0, "load") # unload option of first ferry cargo item
          else:             cursor.toNext()
        elif cursor.selection == "load":
          cursor.selection = "stage"
        elif cursor.selection == "stage" and cursor.isSection("ferry"):
          cursor.selection = "abandon"
        else: cursor.toNext()

      case(pg.K_w):
        if cursor.isSection("option"): # option is selected
          if ferry and ferry.cargo:
            cursor.toSection("ferry", len(ferry.cargo)-1, "load") # last option of ferry
          elif port.stage:
            cursor.toSection("stage", len(port.stage)-1, "load") # last option of stage
          elif port.cargo:
            cursor.toSection("port", len(port.cargo)-1, "load") # last option of port
        # in a cargo section
        elif cursor.row != 0:
          cursor.row = cursor.row - 1
        # top of a section
        elif cursor.isSection("ferry") and port.stage:
          if cursor.selection == "abandon": cursor.selection = "stage"
          cursor.toSection("stage")
          cursor.row = len(port.stage) - 1 # load option of last port stage item
        elif port.cargo:
          cursor.toSection("port")
          cursor.row = len(port.cargo) - 1 # load option of last port cargo item

      case(pg.K_s):
        # in a cargo section
        if cursor.isSection("ferry"):
          if cursor.row == len(ferry.cargo) - 1:
            cursor.toSection("option", 0, "next")
          else: cursor.row += 1
        elif cursor.isSection("stage"):
          if cursor.row == len(port.stage) - 1:
            if ferry and ferry.cargo: cursor.toSection("ferry", 0)
            else: cursor.toSection("option", 0, "next")
          else: cursor.row += 1
        elif cursor.isSection("port"):
          if cursor.row == len(port.cargo) - 1:
            if port.stage: cursor.toSection("stage", 0)
            elif ferry and ferry.cargo: cursor.toSection("ferry", 0)
            else: cursor.toSection("option", 0, "next")
          else: cursor.row += 1

      case(pg.K_SPACE):
        if cursor.isClose():
          return "worldMap"
        elif cursor.isNext() and ferry:
          return "destMenu"
        # if loaded and space in the port, unload
        if cursor.isSection("port"):
          if cursor.selection == "load" and ferry and len(ferry.cargo) < ferry.capacity:
            ferry.cargo.append(port.cargo.pop(cursor.row))
            ferry.cargo.sort(key=lambda item: item.destination.name + str(item))
          elif cursor.selection == "stage" and len(port.stage) < port.stageCapacity:
            port.stage.append(port.cargo.pop(cursor.row))
            port.stage.sort(key=lambda item: item.destination.name + str(item))
          if not port.cargo: cursor.toNext() # TODO: make these go to nearest item?
          cursor.row = min(cursor.row, len(port.cargo)-1)

        elif cursor.isSection("stage"):
          if cursor.selection == "load" and ferry and len(ferry.cargo) < ferry.capacity:
            ferry.cargo.append(port.stage.pop(cursor.row))
            ferry.cargo.sort(key=lambda item: item.destination.name + str(item))
          elif cursor.selection == "stage" and len(port.cargo) < port.cargoCapacity:
            port.cargo.append(port.stage.pop(cursor.row))
            port.cargo.sort(key=lambda item: item.destination.name + str(item))
          if not port.stage: cursor.toNext()
          cursor.row = min(cursor.row, len(port.stage)-1)

        elif cursor.isSection("ferry") and ferry:
          if cursor.selection == "load" and len(port.cargo) < port.cargoCapacity:
            port.cargo.append(ferry.cargo.pop(cursor.row))
            port.cargo.sort(key=lambda item: item.destination.name + str(item))
          elif cursor.selection == "stage" and len(port.stage) < port.stageCapacity:
            port.stage.append(ferry.cargo.pop(cursor.row))
            port.stage.sort(key=lambda item: item.destination.name + str(item))
          elif cursor.selection == "abandon":
            ferry.cargo.pop(cursor.row)
            ferry.cargo.sort(key=lambda item: item.destination.name + str(item))
          if not ferry.cargo: cursor.toNext()
          cursor.row = min(cursor.row, len(ferry.cargo)-1)

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
          return "worldMap"
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
    return "worldMap"
