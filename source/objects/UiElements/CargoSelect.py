from .UiElements import *

class CargoSelect(UiElement):
  def __init__(self):
    log("New CargoSelect")
    pg.sprite.Sprite.__init__(self)
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.cursor = Cursor()

  def draw(self, port: Port, ferry: Ferry) -> None:
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
      self.screen.blit(self.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0] - 40, 20 * (len(port.cargo) + row) + 70)))

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
      text = self.font.render("[ UNSTAGE ]", True, stageColor, stageBackground)
      self.screen.blit(text, text.get_rect(centerx=colSpacing[4] + columns[4].get_width()/2, y=20*row+stageY))
    for row in range(port.stageCapacity - len(port.stage)):
      self.screen.blit(self.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0] - 40, 20 * (len(port.stage) + row) + stageY)))

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
      self.screen.blit(self.font.render("[ ]", True, (255, 255, 255)), ((colSpacing[0]-40, 20 * (len(ferry.cargo) + row) + ferryY)))

  def processKeypress(self, key, port: Port, ferry: Ferry) -> str:
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
          return "worldMap" if len(port.ferries) == 1 else "ferrySelect"
        elif cursor.isNext() and ferry:
          return "destinationSelect"
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

    return "cargoSelect"
