from .UiElements import *

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

  def draw(self, port: Port, ferry: Ferry) -> None:
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
      destColor = (255,255,255)
      if ferry.destination == port:
        destColor = (169,214,229)
      elif len(port.ferries) == port.getFerryCapacity():
        destColor = (150,150,150)
      destination = self.font.render(f"[{port.name:^20}]", True, destColor, \
                              ( 97,165,194) if self.selection-2  == row  else (1,42,74))
      self.screen.blit(destination, ((colSpacing[0], 20*row+70)))

      destItems = [item for item in ferry.cargo if item.destination == port]

      bonus = f"{5 * (len(destItems)-1):>2}%" if destItems else ""
      profit = ((len(destItems)-1)*0.05 + 1) * sum(item.payment for item in destItems)

      self.screen.blit(self.font.render("[X]" * len(destItems), True, (255, 255, 255)), ((colSpacing[1], 20*row+70)))
      self.screen.blit(self.font.render(bonus,                  True, (255, 255, 255)), ((colSpacing[2], 20*row+70)))
      self.screen.blit(self.font.render(f"${profit:>6.0f}",     True, (255, 255, 255)), ((colSpacing[3], 20*row+70)))

    # blit loaded graphic
    slotText = "[X]" * len(ferry.cargo) + "[ ]" * (ferry.getCargoCapacity() - len(ferry.cargo))
    text = self.font.render(slotText, True, (255, 255, 255))
    self.screen.blit(text, text.get_rect(centerx=1920 / 2, y=400))

  def processKeypress(self, key, port: Port, ferry: Ferry) -> str:
    match(key):
      case(pg.K_q):
        return "worldMap"

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
          return GameData.prevUi
        elif self.selection == 1 and ferry.destination:
          if len(ferry.destination.ferries) == ferry.destination.getFerryCapacity():
            log("Selected port has no available docks")
          else:
            port.ferries.remove(ferry)
            # launch ferry
            ferry.distanceFromDest = 5
            ferry.depart()
            return "worldMap"
        elif self.selection >= 2:
          if len(port.destinations[self.selection-2].ferries) == port.destinations[self.selection-2].getFerryCapacity():
            log("Selected port has no available docks")
          if ferry.destination == port.destinations[self.selection-2]:
            ferry.destination = None
          else:
            ferry.destination = port.destinations[self.selection-2]

    return "destinationSelect"
