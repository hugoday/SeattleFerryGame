from .GameElements import *
from assets.assets import StaticAssets
from data.data import *

class StaticElement(GameElement):
  def __init__(self):
    log("New StaticElement")

class Landscape(StaticElement):
  def __init__(self):
    log("New Landscape")
    self.image = StaticAssets.landscape
  
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
    self.name = name
    self.destinations = []
    self.cargo = []
    self.ferries = []
    self.pos = [0,0]
    self.sprite = pg.font.SysFont("consolas", 18).render(name+"IIII", True, (210,180,140), (139,69,19))
    self.berths = 1

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