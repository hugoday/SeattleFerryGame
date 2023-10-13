import pygame as pg
from random import randrange as rand
import random as rnd

from pygame.sprite import *
from assets.assets import *
from data.data import *
from objects.UiElements.UiElements import *
from objects.UiElements.CargoSelect import *
from objects.UiElements.DestinationSelect import *
from objects.UiElements.FerrySelect import *
from objects.UiElements.WorldMap import *
from objects.UiElements.PortUpgrade import *
from objects.MovingElements import *
from objects.StaticElements import *
import os

def main():
  pg.init()
  font = pg.font.SysFont("consolas", 18)
  screenWidth = 1920
  screenHeight = 1080
  screen = pg.display.set_mode((screenWidth, screenHeight))
  clock = pg.time.Clock()
  running = True
  gameState = "startMenu"

  time = 0
  frames = 1
  newJobs = False

  log("Building ports...")
  ports = [Port(name) for name in DataAssets.ports[0:3]]
  for port in ports:
    for dest in ports:
      if dest != port:
        port.newDestination(dest)

  ports[0].pos = [465,175]
  ports[1].pos = [880,845]
  ports[2].pos = [1688,157]
  log("[DONE]")

  log("Building ferries...")
  ferries: Ferry = [Ferry(name) for name in ["Endurance", "Discovery"]]
  for i, ferry in enumerate(ferries):
    ferry.destination = ports[i]
    ferry.arrive()
  log("[DONE]")
  
  log("Building UIs...")
  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()
  cargoSelect = CargoSelect()
  destinationSelect = DestinationSelect()
  worldMap = WorldMap()
  ferrySelect = FerrySelect()
  portUpgrade = PortUpgrade()
  worldMap.ports = ports
  worldMap.ferries = ferries
  worldMap.selection = ports[0]
  log("[DONE]")

  background = pg.Surface(screen.get_size())
  background = background.convert()
  background.fill((0, 0, 153))

  while running:
    for event in pg.event.get():
      if event.type == pg.QUIT:
        running = False
      if event.type != pg.KEYDOWN:
        continue
      if event.key == pg.K_q:
        running = False

      match gameState:
        case "cargoSelect":
          if len(worldMap.selection.ferries) > 1:
            ferry = ferrySelect.selectedFerry
          elif worldMap.selection.ferries:
            ferry = worldMap.selection.ferries[0]
          else:
            ferry = None
          gameState = cargoSelect.processKeypress(event.key, worldMap.selection, ferry)

        case "destinationSelect":
          if len(worldMap.selection.ferries) > 1:
            ferry = ferrySelect.selectedFerry
          elif worldMap.selection.ferries:
            ferry = worldMap.selection.ferries[0]
          else:
            ferry = None
          gameState = destinationSelect.processKeypress(event.key, worldMap.selection, ferry)

        case "startMenu":
          gameState = startMenu.processKeypress(event.key)

        case "worldMap":
          gameState = worldMap.processKeypress(event.key)

        case "ferrySelect":
          gameState = ferrySelect.processKeypress(event.key, worldMap.selection)

        case "portUpgrade":
          gameState = portUpgrade.processKeypress(event.key, worldMap.selection)

    # update screen
    match gameState:
      case "cargoSelect":
        screen.fill((1,42,74))
        if len(worldMap.selection.ferries) > 1:
          ferry = ferrySelect.selectedFerry
        elif worldMap.selection.ferries:
          ferry = worldMap.selection.ferries[0]
        else:
          ferry = None
        cargoSelect.draw(worldMap.selection, ferry)
      case "destinationSelect":
        screen.fill((1,42,74))
        if len(worldMap.selection.ferries) > 1:
          ferry = ferrySelect.selectedFerry
        elif worldMap.selection.ferries:
          ferry = worldMap.selection.ferries[0]
        else:
          ferry = None
        destinationSelect.draw(worldMap.selection, ferry)
      case "startMenu":
        screen.fill((1,42,74))
        startMenu.draw()
      case "worldMap":
        worldMap.draw()
        creditsDisplay.draw()
      case "ferrySelect":
        screen.fill((1,42,74))
        ferrySelect.draw(worldMap.selection)
      case "portUpgrade":
        screen.fill((1,42,74))
        portUpgrade.draw(worldMap.selection)
      case "quit":
          running = False

    pg.display.flip()
    clock.tick(30)
    frames += 1
    if frames % 30 == 0:
      frames = 0
      time += 1
      #update every second
      for ferry in ferries:
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
      for port in ports:
        # 25% chance of being removed
        for item in port.cargo:
          if randint(1,4) == 1: # and isn't special
            port.cargo.remove(item)
        # add 1/4 of capacity
        for _ in range(port.cargoCapacity // 4):
          if len(port.cargo) == port.cargoCapacity:
            break
          port.newRandomCargo()
        port.cargo.sort(key=lambda item: item.destination.name + str(item))
      newJobs = False

  pg.quit()


main_dir = os.path.split(os.path.abspath(__file__))[0]
assetDir = os.path.join(main_dir, "assets")

main()