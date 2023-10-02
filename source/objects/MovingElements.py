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
  def __init__(self, port) -> None:
    log("New Ferry")
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("ferry.png", scale=0.3)
    screen = pg.display.get_surface()
    self.area = screen.get_rect()
    self.pos = [0,0]
    self.rect.topleft = self.pos
    self.cargo = []
    self.destination = None
    self.port = port
    self.moving = False
    self.distanceFromDest = 0
    self.capacity = 4

  def update(self):
    self.pos[0] += 1
    self.pos[1] += 1
    # check if arrived
    if self.distanceFromDest == 0:
      log("ferry arrived at " + self.destination.name)
      self.port = self.destination
      self.moving = False

  def addCargo(self, item:Cargo):
    if not item:
      log("Cannot load empty cargo item", 1)
      return
    log("Loaded cargo item onto ferry")
    self.cargo.append(item)

  def depart(self):
    if not self.destination:
      log("Cannot go to None destination", 1)
      return
    log("Ferry heading from " + self.port.name + " to " + self.destination.name)
    # self.port = self.destination
    self.moving = True