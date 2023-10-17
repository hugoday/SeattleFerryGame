from logger import log
from assets.assets import DataAssets
from random import randint
import pygame as pg

class Cargo():
  def __init__(self, \
               source="Source", \
               destination="Dest", \
               contents="Empty", \
               payment=0):

    self.source = source
    self.destination = destination
    self.contents = contents
    self.payment = payment
    self.font = pg.font.SysFont("consolas", 18)
    # log(f"New Cargo: {contents:^14} from  {source.name:^20} to {destination.name:^20} for {str(payment):<6}")

  def setSource(self, source):
    self.source = source

  def setPayment(self, payment):
    self.payment = payment

class GameData:
  credits = 10000
  maxCargoPayment = 1000
  minCargoPayment = 100