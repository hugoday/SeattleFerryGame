from logger import log
from assets.assets import DataAssets
from random import randint
from objects.GameElements import GameElement
from data.data import Cargo
from objects.StaticElements import Port
import pygame as pg
import pickle
import os
import copy

from data.data import GameData

class SaveGame():
  def __init__(self):
    pass

  # savePath = os.path.join(os.path.dirname(__file__), "save")
  # savePath = os.path.join(savePath, "savegame")
  savePath = 'D:\\SeattleFerryGame\\source\\save\\savegame'

  def checkSave():
    try:
      pickle.load(open(SaveGame.savePath, "rb"))
      return True
    except:
      return False

  def saveGame():
    saveFile = open(SaveGame.savePath, "wb")
    ferryData = []
    portData = []

    for ferry in GameData.ferries:
      ferryCopy = copy.copy(ferry)
      del ferryCopy.sprite
      del ferryCopy._Sprite__g

      ferryCopy.destination = ferryCopy.destination.name
      ferryCopy.port = ferryCopy.port.name
      ferryCopy.cargo = [copy.copy(item) for item in ferry.cargo]
      for i, item in enumerate(ferryCopy.cargo):
        del item.font
        item.source = item.source.name
        item.destination = item.destination.name
      ferryData.append(ferryCopy)

    for port in GameData.getPorts():
      portCopy = copy.copy(port)
      del portCopy.sprite
      del portCopy._Sprite__g
      del portCopy.destinations
      del portCopy.ferries
      del portCopy.cargo

      portCopy.stage = [copy.copy(item) for item in port.stage]
      for i, item in enumerate(portCopy.stage):
        item.source = item.source.name
        item.destination = item.destination.name
        item.font = item.fontName
        portCopy.stage[i] = item
      portData.append(portCopy)
      # print(portCopy.__dict__)
    gamedata = [ferryData, portData, GameData.credits]
    pickle.dump(gamedata, saveFile)
    saveFile.close()

  def loadGame():
    def getPort(name):
      for port in GameData.getPorts():
        if port.name == name:
          return port
      return None

    saveFile = open(SaveGame.savePath, "rb")
    ferries, portSaves, GameData.credits = pickle.load(saveFile)
    Port.buildPorts()

    for ferry in ferries:
      pg.sprite.Sprite.__init__(ferry)
      ferry.sprite, ferry.rect = GameElement.load_image("ferry.png", scale=0.2)
      ferry.destination = getPort(ferry.destination)
      ferry.port = getPort(ferry.port)
      for i, item in enumerate(ferry.cargo):
        ferry.cargo[i] = Cargo(source=getPort(item.source), \
                               destination=getPort(item.destination), \
                               contents=item.contents, \
                               payment=item.payment, \
                               fontName=item.fontName)
    GameData.ferries = ferries

    for index, port in enumerate(GameData.getPorts()):
      port.ferries = [ferry for ferry in ferries if ferry.port.name == port.name]
      port.cargoCapacityLevel = portSaves[index].cargoCapacityLevel
      port.stageCapacityLevel = portSaves[index].stageCapacityLevel
      port.ferryCapacityLevel = portSaves[index].ferryCapacityLevel
      for item in portSaves[index].stage:
        port.stage.append(Cargo(source=getPort(item.source), \
                               destination=getPort(item.destination), \
                               contents=item.contents, \
                               payment=item.payment, \
                               fontName=item.fontName))
