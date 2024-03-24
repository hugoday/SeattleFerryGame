from .GameElements import *
from data.data import *

class MovingElement(GameElement):
  def __init__(self):
    log("New MovingElement")

class Ferry(MovingElement):
  def buildFerries():
    GameData.ferries = [Ferry(name) for name in ["Endurance", "Discovery"]]
    for i, ferry in enumerate(GameData.ferries):
      ferry.destination = GameData.ports[i]
      ferry.arrive()

  def __init__(self, name="Name", \
               cargoCapacityLevels=[4,5,6], efficiencyLevels=[1.0,0.9,0.8], \
               cargoCapacityPrices=[10000,12000,14000], efficiencyPrices=[10000,12000,14000]) -> None:
    log("New Ferry")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("ferry.png", scale=0.2)
    self.pos = [0,0]
    self.cargo = []
    self.destination = None
    self.port = None
    self.moving = False
    self.distanceFromDest = 0
    self.name = name
    # Upgrade progressions
    self.cargoCapacityLevels = cargoCapacityLevels
    self.efficiencyLevels = efficiencyLevels
    self.cargoCapacityPrices = cargoCapacityPrices
    self.efficiencyPrices = efficiencyPrices
    # Upgradable stats
    self.cargoCapacityLevel = 0
    self.efficiencyLevel = 0

  def getCargoCapacity(self):
    return self.cargoCapacityLevels[self.cargoCapacityLevel]

  def getEfficiency(self):
    return self.efficiencyLevels[self.efficiencyLevel]

  def update(self):
    self.pos[0] -= 2
    self.pos[1] += 2

  def addCargo(self, item):
    if not item:
      log("Cannot load empty cargo item", 1)
      return
    if len(self.cargo) >= self.getCargoCapacity():
      log("Ferry cannot hold more cargo", 1)
      return
    log("Loaded cargo item onto ferry")
    self.cargo.append(item)
    self.cargo.sort(key=lambda item: f"{item.destination.name}{GameData.maxCargoPayment-item.payment:0>4}{item}")

  def hasCargoSpace(self):
    if len(self.cargo) < self.getCargoCapacity():
      return True
    return False

  def depart(self):
    if not self.destination:
      log("Cannot go to None destination", 1)
      return
    log("Ferry heading from " + self.port.name + " to " + self.destination.name)
    # self.port = self.destination
    self.moving = True

  def arrive(self):
    # ferry
    self.port = self.destination
    self.moving = False
    self.pos = [self.port.pos[0] - 90, self.port.pos[1] - 90]
    log("Ferry port set to " + self.port.name)

    # port
    self.port.ferries.append(self)

    destItems = [item for item in self.cargo if item.destination == self.port]
    profit = ((len(destItems)-1)*0.05 + 1) * sum(item.payment for item in destItems)

    for item in destItems:
      self.cargo.remove(item)

    return int(profit)
