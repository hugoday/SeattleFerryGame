from .UiElements import *

class PortUpgrade(UiElement):
  def __init__(self):
    log("New PortUpgrade")
    pg.sprite.Sprite.__init__(self)
    # internal objects
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.cursor = Cursor()
    self.cursor.toSection(row=0, section="upgrade", selection="UPGRADE")

  def draw(self, port: Port) -> None:
    columns = [self.font.render(item, True, (255, 255, 255)) for item in \
               ["Attribute", "Current", "Next", "Max", "Price", "Upgrade", "Level"]]
    colSpacing = [600, 800, 900, 1000, 1100, 1250, 1400]
    upgrades = [["Cargo Capacity", port.cargoCapacity, port.cargoCapacityLevels, port.cargoCapacityPrices], \
                ["Stage Capacity", port.stageCapacity, port.stageCapacityLevels, port.stageCapacityPrices], \
                ["Ferry Capacity",  port.ferryCapacity, port.ferryCapacityLevels, port.ferryCapacityPrices]]
    
    title = self.font.render("Port upgrade:", True, (255, 255, 255))
    close = self.font.render("[  Close  ]", True, (255, 255, 255), (97,165,194) if self.cursor.isClose() else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=400))

    # draw column headers
    for col, attribute in enumerate(columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    def centerOnColumn(text, col, color=(255,255,255), background=None):
      render = self.font.render(text, True, color, background)
      pos = render.get_rect(centerx=colSpacing[col] + columns[col].get_width()/2, y=20*row+70)
      return render, pos
    
    # blit ports
    for row, upgrade in enumerate(upgrades):
      currentLevel = upgrade[2].index(upgrade[1])
      # Attribute
      self.screen.blit(self.font.render(upgrade[0], True, (255, 255, 255)), ((colSpacing[0], 20*row+70)))
      # Current
      # current = self.font.render(f"{upgrade[1]:>3}", True, (255, 255, 255))
      self.screen.blit(*centerOnColumn(f"{upgrade[1]:>3}", 1))
      # Next
      next = f"{upgrade[2][currentLevel+1]:>3}" if currentLevel < len(upgrade[2])-1 else "---"
      self.screen.blit(*centerOnColumn(next, 2))
      # Max
      self.screen.blit(*centerOnColumn(f"{upgrade[2][-1]:>3}", 3))
      # Price
      price = f"{upgrade[3][currentLevel+1]:>6}" if currentLevel < len(upgrade[2])-1 else ""
      self.screen.blit(*centerOnColumn(price, 4))
      # Upgrade
      if self.cursor.row == row and not self.cursor.isClose():
        text = f"[ {self.cursor.selection} ]"
      else:
        text = "[ UPGRADE ]"
      if currentLevel < len(upgrade[2])-1 and upgrade[3][currentLevel+1] <= GameData.credits:
        textColor = (255,255,255)
      else:
        textColor = (150,150,150)
      upgradeBackground = ( 97,165,194) if self.cursor.row == row and not self.cursor.isClose() else (1,42,74)
      self.screen.blit(*centerOnColumn(text, color=textColor, background=upgradeBackground, col=5))
      # Level graohic
      levelText = "[" + "+"*(currentLevel+1) + "-"*(len(upgrade[2])-currentLevel-1) + "]"
      self.screen.blit(self.font.render(levelText, True, (255,255,255)), (colSpacing[6], 20*row+70))

  def processKeypress(self, key, port: Port) -> str:
    match(key):
      case(pg.K_a):
        self.cursor.toClose()

      case(pg.K_d):
        self.cursor.toSection(row=0, section="upgrade", selection="UPGRADE")

      case(pg.K_w): # TODO: Checking if options exist below
        if self.cursor.isClose():
          self.cursor.toSection(row=2, section="upgrade", selection="UPGRADE")
        elif self.cursor.row > 0:
          self.cursor.selection = "UPGRADE"
          self.cursor.row -= 1

      case(pg.K_s):
        if self.cursor.row == 2:
          self.cursor.toClose()
        elif not self.cursor.isClose():
          self.cursor.selection = "UPGRADE"
          self.cursor.row += 1

      case(pg.K_SPACE):
        if self.cursor.isClose():
          return "worldMap"
        elif self.cursor.selection == "UPGRADE":
          self.cursor.selection = "CONFIRM"
        else: # TODO: make this DRY
          # attr = self.cursor.row
          # capacities = [port.cargoCapacity, port.stageCapacity, port.ferryCapacity]
          # levels = [port.cargoCapacityLevels, port.stageCapacityLevels, port.ferryCapacityLevels]
          # prices = [port.cargoCapacityPrices, port.stageCapacityPrices, port.ferryCapacityPrices]
          # currentLevel = levels[attr].index(capacities[attr])
          # if currentLevel < len(levels[attr])-1 and \
          #       GameData.credits >= prices[attr][currentLevel + 1]:
          #   capacities[attr] = levels[attr][currentLevel + 1]
          #   GameData.credits -= prices[attr][currentLevel + 1]
          #   self.cursor.selection = "UPGRADE"
          match self.cursor.row:
            case 0: # Cargo capacity
                currentLevel = port.cargoCapacityLevels.index(port.cargoCapacity)
                if currentLevel < len(port.cargoCapacityLevels)-1 and \
                      GameData.credits >= port.cargoCapacityPrices[currentLevel + 1]:
                  port.cargoCapacity = port.cargoCapacityLevels[currentLevel + 1]
                  GameData.credits -= port.cargoCapacityPrices[currentLevel + 1]
            case 1: # Stage capacity
              currentLevel = port.stageCapacityLevels.index(port.stageCapacity)
              if currentLevel < len(port.stageCapacityLevels)-1 and \
                    GameData.credits >= port.stageCapacityPrices[currentLevel + 1]:
                port.stageCapacity = port.stageCapacityLevels[currentLevel + 1]
                GameData.credits -= port.stageCapacityPrices[currentLevel + 1]
            case 2: # Ferry capacity
              currentLevel = port.ferryCapacityLevels.index(port.ferryCapacity)
              if currentLevel < len(port.ferryCapacityLevels)-1 and \
                    GameData.credits >= port.ferryCapacityPrices[currentLevel + 1]:
                port.ferryCapacity = port.ferryCapacityLevels[currentLevel + 1]
                GameData.credits -= port.ferryCapacityPrices[currentLevel + 1]
          self.cursor.selection = "UPGRADE"

    return "portUpgrade"
  
