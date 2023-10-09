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
  def __init__(self, name):
    log("New Port: " + name)
    pg.sprite.Sprite.__init__(self)
    self.sprite, self.rect = GameElement.load_image("dock.png", scale=0.8)
    self.sprite = pg.transform.rotate(self.sprite, 90)
    self.name = name
    self.destinations = []
    self.ferries = []
    self.cargo = []
    self.stage = []
    self.pos = [0,0]
    self.docks = 1
    self.cargoCapacity = 10
    self.stageCapacity = 4

  def newRandomCargo(self):
    if not self.destinations:
      log("No known ports to send cargo to", 1)
      return
    self.cargo.append(Cargo(source=self, \
                        destination=self.destinations[randint(0,len(self.destinations)-1)], \
                        contents=DataAssets.cargoContents[randint(0,len(DataAssets.cargoContents)-1)], \
                        payment=randint(10,1000)))

  def newDestination(self, port):
    if port in self.destinations:
      log("Port already in destinations", 1)
      return
    if port == self:
      log("Cannot add self to destinations", 1)
      return
    log("Added " + port.name + " to " + self.name + " destinations")
    self.destinations.append(port)