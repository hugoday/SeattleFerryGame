from logger import log
import pygame as pg

class Cargo():
  def __init__(self, \
               source="Source", \
               destination="Dest", \
               contents="Empty", \
               payment=0, \
               fontName="consolas"):

    self.source = source
    self.destination = destination
    self.contents = contents
    self.payment = payment
    self.fontName = fontName
    self.font = pg.font.SysFont(fontName, 18)
    # log(f"New Cargo: {contents:^14} from  {source.name:^20} to {destination.name:^20} for {str(payment):<6}")

  def setSource(self, source):
    self.source = source

  def setPayment(self, payment):
    self.payment = payment

class GameData:
  credits = 10000
  maxCargoPayment = 1000
  minCargoPayment = 100
  uiFerry = None
  ports = []
  ferries = []
  prevUi = ""

  def getPorts():
    return GameData.ports[0:-1]
  
  def getShipyard():
    return GameData.ports[-1]