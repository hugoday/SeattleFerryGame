from .GameElements import *
from assets.assets import StaticAssets
from data.data import *

class StaticElement(GameElement):
  def __init__(self):
    log("New StaticElement")

class Landscape(StaticElement):
  def __init__(self):
    log("New Landscape")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("islandsMap2.png", scale=1)
    screen = pg.display.get_surface()
    self.area = screen.get_rect()
    self.pos = [0,0]

class Island(StaticElement):
  def __init__(self):
    log("New Island")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("island.png", scale=0.8)
    screen = pg.display.get_surface()
    self.area = screen.get_rect()
    self.pos = [0,0]

class Tree(StaticElement):
  def __init__(self, style):
    log("New Tree")
    self.image = ["No image"]

class House(StaticElement):
  def __init__(self, style):
    log("New House")
    self.image = ["No image"]

class Bouy(StaticElement):
  def __init__(self, style):
    log("New Bouy")
    self.image = StaticAssets.markers[0]

class RouteLine(StaticElement):
  def __init__(self):
    log("New RouteLine")
    self.image = ["No image"]

class Port(StaticElement):
  def __init__(self, name="Port", \
               ferryCapacityLevels=[1,2,3], cargoCapacityLevels=[8,10,12,14,16], stageCapacityLevels=[4,6,8], \
               ferryCapacityPrices=[0,10000,20000], cargoCapacityPrices=[0,1000,1200,1400,1600], stageCapacityPrices=[0,6000,8000]):
    log("New Port: " + name)
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("dock.png", scale=0.8)
    self.sprite = pg.transform.rotate(self.sprite, 90)
    self.name = name
    self.pos = [0,0]
    self.destinations = []
    # Variable contents
    self.ferries = []
    self.cargo = []
    self.stage = []
    # Upgrade progressions
    self.ferryCapacityLevels = ferryCapacityLevels
    self.cargoCapacityLevels = cargoCapacityLevels
    self.stageCapacityLevels = stageCapacityLevels
    self.ferryCapacityPrices = ferryCapacityPrices
    self.cargoCapacityPrices = cargoCapacityPrices
    self.stageCapacityPrices = stageCapacityPrices
    # Upgradable stats
    self.ferryCapacity = self.ferryCapacityLevels[0]
    self.cargoCapacity = self.cargoCapacityLevels[0]
    self.stageCapacity = self.stageCapacityLevels[0]

  def newRandomCargo(self):
    if not self.destinations:
      log("No known ports to send cargo to", 1)
      return
    self.cargo.append(Cargo(source=self, \
                        destination=self.destinations[randint(0,len(self.destinations)-1)], \
                        contents=DataAssets.cargoContents[randint(0,len(DataAssets.cargoContents)-1)], \
                        payment=randint(GameData.minCargoPayment,GameData.maxCargoPayment)))

  def newDestination(self, port):
    if port in self.destinations:
      log("Port already in destinations", 1)
      return
    if port == self:
      log("Cannot add self to destinations", 1)
      return
    log("Added " + port.name + " to " + self.name + " destinations")
    self.destinations.append(port)

  def addCargo(self, item: Cargo):
    if not item:
      log("Cannot load empty cargo item", 1)
      return
    if len(self.cargo) >= self.cargoCapacity:
      log("Port cannot hold more cargo", 1)
      return
    log("Loaded cargo item into port")
    self.cargo.append(item)
    self.cargo.sort(key=lambda item: f"{item.destination.name}{GameData.maxCargoPayment-item.payment:0>4}{item}")

  def hasCargoSpace(self):
    if len(self.cargo) < self.cargoCapacity:
      return True
    return False

  def addStage(self, item: Cargo):
    if not item:
      log("Cannot stage empty cargo item", 1)
      return
    if len(self.stage) >= self.stageCapacity:
      log("Port cannot stage more cargo", 1)
      return
    log("Loaded cargo item into stage")
    self.stage.append(item)
    self.stage.sort(key=lambda item: f"{item.destination.name}{GameData.maxCargoPayment-item.payment:0>4}{item}")

  def hasStageSpace(self):
    if len(self.stage) < self.stageCapacity:
      return True
    return False
