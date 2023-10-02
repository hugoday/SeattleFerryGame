from logger import log
from assets.assets import DataAssets
from random import randint

class Cargo():
  def __init__(self, \
               source="Source", \
               destination="Dest", \
               contents="Empty", \
               payment=0):

    self.source = source
    self.destination = destination
    self.contents = contents #random cargo
    self.payment = payment
    log(f"New Cargo: {contents:^14} from  {source.name:^20} to {destination.name:^20} for {str(payment):<6}")

  def setSource(self, source):
    self.source = source

  def setPayment(self, payment):
    self.payment = payment

  # def toggleLoad(self):
  #   if self.loaded:
  #     self.loaded = False
  #   else:
  #     self.loaded = True

credits = 1000