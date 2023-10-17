from .GameElements import *
from data.data import *

class MovingElement(GameElement):
  def __init__(self):
    log("New MovingElement")

class Boat(MovingElement):
  def __init__(self, style):
    log("New Boat")
    self.image = ["No image"]

class Ferry(MovingElement):
  def __init__(self, name="Name") -> None:
    log("New Ferry")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("ferry.png", scale=0.2)
    # self.sprite = pg.transform.rotate(self.sprite, -90)
    screen = pg.display.get_surface()
    self.area = screen.get_rect()
    self.pos = [0,0]
    self.rect.topleft = self.pos
    self.cargo = []
    self.destination = None
    self.port = None
    self.moving = False
    self.distanceFromDest = 0
    self.capacity = 4
    self.name = name

  def update(self):
    self.pos[0] -= 2
    self.pos[1] += 2

  def addCargo(self, item:Cargo):
    if not item:
      log("Cannot load empty cargo item", 1)
      return
    if len(self.cargo) >= self.capacity:
      log("Ferry cannot hold more cargo", 1)
      return
    log("Loaded cargo item onto ferry")
    self.cargo.append(item)
    self.cargo.sort(key=lambda item: f"{item.destination.name}{GameData.maxCargoPayment-item.payment:0>4}{item}")
  
  def hasCargoSpace(self):
    if len(self.cargo) < self.capacity:
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
