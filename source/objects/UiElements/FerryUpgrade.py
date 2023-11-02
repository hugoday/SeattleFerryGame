from .UiElements import *

class FerryUpgrade(UiElement):
  def __init__(self):
    log("New FerryUpgrade")
    pg.sprite.Sprite.__init__(self)
    # internal objects
    self.screen = pg.display.get_surface()
    self.font = pg.font.SysFont("consolas", 18)
    self.cursor = Cursor()
    self.cursor.toNext()

  def draw(self, ferry: Ferry) -> None:
    columns = [self.font.render(item, True, (255, 255, 255)) for item in \
               ["Attribute", "Current", "Next", "Max", "Price", "Upgrade", "Level"]]
    colSpacing = [600, 800, 900, 1000, 1100, 1250, 1400]
    if ferry:
      upgrades = [["Cargo Capacity", ferry.cargoCapacityLevel, ferry.cargoCapacityLevels, ferry.cargoCapacityPrices], \
                  # ["Speed", ferry.getSpeed(), ferry.stageCapacityLevels, ferry.stageCapacityPrices], \
                  ["Efficiency",  ferry.efficiencyLevel, ferry.efficiencyLevels, ferry.efficiencyPrices]]
    else:
      upgrades = [["Cargo Capacity", 0, ["---"], ["---"]], \
                # ["Speed", ferry.getSpeed(), ferry.stageCapacityLevels, ferry.stageCapacityPrices], \
                ["Efficiency", 0, ["---"], ["---"]]]
    
    title = self.font.render("Ferry upgrade:", True, (255, 255, 255))
    close = self.font.render("[  Close  ]", True, (255, 255, 255), (97,165,194) if self.cursor.isClose() else (1,42,74))
    next   = self.font.render("[  Depart  ]", True, (255, 255, 255) if ferry else (150,150,150), \
                              (97,165,194) if self.cursor.isNext() else (1,42,74))

    # blit header and menu buttons
    self.screen.blit(title, title.get_rect(centerx=1920 / 2, y=10))
    self.screen.blit(close, close.get_rect(centerx=1920 / 5, y=400))
    self.screen.blit(next, next.get_rect(centerx=1920 / 5 * 4, y=400))

    # draw column headers
    for col, attribute in enumerate(columns):
      self.screen.blit(attribute, (colSpacing[col], 50))
    pg.draw.line(self.screen, (255, 255, 255), (10,65),(6150,65))

    def centerOnColumn(text, col, color=(255,255,255), background=None):
      render = self.font.render(text, True, color, background)
      pos = render.get_rect(centerx=colSpacing[col] + columns[col].get_width()/2, y=20*row+70)
      return render, pos
    
    # draw upgrades
    for row, upgrade in enumerate(upgrades):
      # Attribute
      self.screen.blit(self.font.render(upgrade[0], True, (255, 255, 255)), ((colSpacing[0], 20*row+70)))
      # Current
      self.screen.blit(*centerOnColumn(f"{upgrade[2][upgrade[1]]:>3}", 1))
      # Next
      next = f"{upgrade[2][upgrade[1]+1]:>3}" if upgrade[1] < len(upgrade[2])-1 else "---"
      self.screen.blit(*centerOnColumn(next, 2))
      # Max
      self.screen.blit(*centerOnColumn(f"{upgrade[2][-1]:>3}", 3))
      # Price
      price = f"{upgrade[3][upgrade[1]+1]:>6}" if upgrade[1] < len(upgrade[2])-1 else ""
      self.screen.blit(*centerOnColumn(price, 4))
      # Upgrade
      if not ferry:
        text = ""
      elif self.cursor.isSection("upgrade") and self.cursor.row == row:
        text = f"[ {self.cursor.selection} ]"
      else:
        text = "[ UPGRADE ]"
      if upgrade[1] < len(upgrade[2])-1 and upgrade[3][upgrade[1]+1] <= GameData.credits:
        textColor = (255,255,255)
      else:
        textColor = (150,150,150)
      upgradeBackground = ( 97,165,194) if self.cursor.row == row and ferry and self.cursor.isSection("upgrade") else (1,42,74)
      self.screen.blit(*centerOnColumn(text, color=textColor, background=upgradeBackground, col=5))
      # Level graohic
      levelText = "[" + "+"*(upgrade[1]+1) + "-"*(len(upgrade[2])-upgrade[1]-1) + "]" if ferry else ""
      self.screen.blit(self.font.render(levelText, True, (255,255,255)), (colSpacing[6], 20*row+70))

  def processKeypress(self, key, ferry: Ferry) -> str:
    match(key):
      case(pg.K_q):
        return "worldMap"

      case(pg.K_a):
        if self.cursor.isNext() and ferry:
          self.cursor.toSection(row=0, section="upgrade", selection="UPGRADE")
        else:
          self.cursor.toClose()

      case(pg.K_d):
        if self.cursor.isClose() and ferry:
          self.cursor.toSection(row=0, section="upgrade", selection="UPGRADE")
        else:
          self.cursor.toNext()

      case(pg.K_w):
        if self.cursor.isClose():
          self.cursor.toSection(row=1, section="upgrade", selection="UPGRADE")
        elif self.cursor.row > 0:
          self.cursor.selection = "UPGRADE"
          self.cursor.row -= 1

      case(pg.K_s):
        if self.cursor.row == 1:
          self.cursor.toClose()
        elif not self.cursor.isClose():
          self.cursor.selection = "UPGRADE"
          self.cursor.row += 1

      case(pg.K_SPACE):
        if self.cursor.isClose():
          return "worldMap"
        elif self.cursor.isNext() and ferry:
          GameData.prevUi = "ferryUpgrade"
          return "destinationSelect"
        elif self.cursor.selection == "UPGRADE":
          self.cursor.selection = "CONFIRM"
        elif self.cursor.section == "upgrade":
          match self.cursor.row:
            case 0: # Cargo capacity
                if ferry.cargoCapacityLevel < len(ferry.cargoCapacityLevels) - 1 and \
                      GameData.credits >= ferry.cargoCapacityPrices[ferry.cargoCapacityLevel + 1]:
                  ferry.cargoCapacityLevel += 1
                  GameData.credits -= ferry.cargoCapacityPrices[ferry.cargoCapacityLevel]
            case 1: # Efficiency
              if ferry.efficiencyLevel < len(ferry.efficiencyLevels) - 1 and \
                    GameData.credits >= ferry.efficiencyPrices[ferry.efficiencyLevel + 1]:
                ferry.efficiencyLevel += 1
                GameData.credits -= ferry.efficiencyPrices[ferry.efficiencyLevel]
          self.cursor.selection = "UPGRADE"

    return "ferryUpgrade"
