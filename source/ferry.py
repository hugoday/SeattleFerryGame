import pygame as pg
from random import randrange as rand
import random as rnd
import pickle
import os
import copy

from assets.assets import *
from data.data import *
from data.SaveGame import *
from objects.MovingElements import *
from objects.StaticElements import *
from objects.UiElements.CargoSelect import *
from objects.UiElements.DestinationSelect import *
from objects.UiElements.FerrySelect import *
from objects.UiElements.PortUpgrade import *
from objects.UiElements.FerryUpgrade import *
from objects.UiElements.StartMenu import *
from objects.UiElements.UiElements import *
from objects.UiElements.WorldMap import *
from pygame.sprite import *

def main():
  import ctypes
  ctypes.windll.user32.SetProcessDPIAware()
  pg.init()
  font = pg.font.SysFont("consolas", 18)
  screenWidth = 1920
  screenHeight = 1080
  screen = pg.display.set_mode((screenWidth, screenHeight))
  clock = pg.time.Clock()
  running = True
  gameState = "startMenu"

  saveFound = SaveGame.checkSave()

  time = 0
  frames = 1
  newJobs = False
  
  log("Building UIs...")
  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()
  cargoSelect = CargoSelect()
  destinationSelect = DestinationSelect()
  worldMap = WorldMap()
  ferrySelect = FerrySelect()
  portUpgrade = PortUpgrade()
  ferryUpgrade = FerryUpgrade()
  log("[DONE]")

  while running:
    for event in pg.event.get():
      if event.type == pg.QUIT:
        running = False
      if event.type != pg.KEYDOWN:
        continue
      if gameState == "worldMap" and event.key == pg.K_q:
        running = False
      if event.key == pg.K_v:
        SaveGame.saveGame()

      match gameState:
        case "cargoSelect":
          gameState = cargoSelect.processKeypress(event.key, worldMap.selection, GameData.uiFerry)
        case "destinationSelect":
          gameState = destinationSelect.processKeypress(event.key, worldMap.selection, GameData.uiFerry)
        case "startMenu":
          gameState = startMenu.processKeypress(event.key, worldMap)
        case "worldMap":
          gameState = worldMap.processKeypress(event.key)
        case "ferrySelect":
          gameState = ferrySelect.processKeypress(event.key, worldMap.selection)
        case "portUpgrade":
          gameState = portUpgrade.processKeypress(event.key, worldMap.selection)
        case "ferryUpgrade":
          gameState = ferryUpgrade.processKeypress(event.key, GameData.uiFerry)
        case _:
          log("Unrecognized gamestate:", gameState, level=1)


    # update screen
    match gameState:
      case "cargoSelect":
        screen.fill((1,42,74))
        cargoSelect.draw(worldMap.selection, GameData.uiFerry)
      case "destinationSelect":
        screen.fill((1,42,74))
        destinationSelect.draw(worldMap.selection, GameData.uiFerry)
      case "startMenu":
        screen.fill((1,42,74))
        startMenu.draw(saveFound)
      case "worldMap":
        worldMap.draw()
        creditsDisplay.draw()
      case "ferrySelect":
        screen.fill((1,42,74))
        ferrySelect.draw(worldMap.selection)
      case "portUpgrade":
        screen.fill((1,42,74))
        portUpgrade.draw(worldMap.selection)
      case "ferryUpgrade":
        screen.fill((1,42,74))
        ferryUpgrade.draw(GameData.uiFerry)
      case "quit":
          running = False
      case _:
          log("Unrecognized gamestate:", gameState, level=1)

    pg.display.flip()
    clock.tick(30)
    frames += 1
    if frames % 30 == 0:
      frames = 0
      time += 1
      #update every second
      for ferry in GameData.ferries:
        if ferry.moving:
          ferry.distanceFromDest -= 1
          ferry.update()
          # check if arrived
          if ferry.distanceFromDest == 0:
            log("ferry arrived at " + ferry.destination.name)
            GameData.credits += ferry.arrive()

    # refresh/new jobs occasionally
    if time % 10 == 0:
      newJobs = True

    if newJobs and gameState == "worldMap":
      for port in GameData.getPorts():
        # 25% chance of being removed
        for item in port.cargo:
          if randint(1,4) == 1: # and isn't special
            port.cargo.remove(item)
        # add 1/4 of capacity
        for _ in range(port.getCargoCapacity() // 4):
          if port.hasCargoSpace():
            port.newRandomCargo()
        port.cargo.sort(key=lambda item: f"{item.destination.name}{GameData.maxCargoPayment-item.payment:0>4}{item}")
      newJobs = False

  pg.quit()


main_dir = os.path.split(os.path.abspath(__file__))[0]
assetDir = os.path.join(main_dir, "assets")

main()