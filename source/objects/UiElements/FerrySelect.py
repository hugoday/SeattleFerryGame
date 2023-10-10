from .UiElements import *

class FerrySelect(UiElement):
  def __init__(self):
    log("New FerrySelect")
    pg.sprite.Sprite.__init__(self)
    # internal objects
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.selection = 2 # 0 = close, 1 = next
    self.selectedFerry = None

  def draw(self, port: Port) -> None:
    columns = [self.font.render(item, True, (255, 255, 255)) for item in ["Ferry", "Cargo", ]]
    colSpacing = [600, 850, 1100, 1200]
    title = self.font.render("Select ferry:", True, (255, 255, 255))
    close = self.font.render("[  Close  ]", True, (255, 255, 255), (97,165,194) if self.selection == 0 else (1,42,74))
    next = self.font.render("[  ---->  ]", True, (255, 255, 255), (97,165,194) if self.selection == 1 else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=400))
    self.screen.blit(next, next.get_rect(centerx=1920 / 5 * 4, y=400))

    # draw column headers
    for col, attribute in enumerate(columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    # blit ports
    for row, ferry in enumerate(port.ferries):
      text = self.font.render(f"[{ferry.name:^20}]", True, \
                              (169,214,229) if self.selectedFerry == ferry else (255,255,255), \
                              ( 97,165,194) if self.selection-2 == row  else (1,42,74))
      self.screen.blit(text, ((colSpacing[0], 20*row+70)))
      self.screen.blit(self.font.render("[X]" * len(ferry.cargo), True, (255, 255, 255)), ((colSpacing[1], 20*row+70)))

  def processKeypress(self, key, port: Port) -> str:
    match(key):
      case(pg.K_a):
        if   self.selection == 1: self.selection = 2
        elif self.selection >= 2: self.selection = 0

      case(pg.K_d):
        if   self.selection == 0: self.selection = 2
        elif self.selection >= 2: self.selection = 1

      case(pg.K_w):
        if   self.selection in [0, 1]:  self.selection = len(port.ferries) + 1
        elif self.selection > 2:        self.selection -= 1

      case(pg.K_s):
        if   self.selection == len(port.ferries) + 1:  self.selection = 1
        elif self.selection >= 2:                      self.selection += 1

      case(pg.K_SPACE):
        if self.selection == 0:
          return "worldMap"
        elif self.selection == 1 and self.selectedFerry:
          return "cargoSelect"
        else:
          self.selectedFerry = port.ferries[self.selection-2]

    return "ferrySelect"
