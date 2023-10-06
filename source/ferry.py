import pygame as pg
from random import randrange as rand
import random as rnd

from pygame.sprite import *
from assets.assets import *
from data.data import *
from objects.UiElements import *
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

  # log("Building islands...")
  # islands: Island = [Island() for _ in range(3)]
  # islands[0].pos = [200,200]
  # islands[1].pos = [400,600]
  # islands[2].pos = [500,150]
  # log("[DONE]")

  log("Building ports...")
  ports = [Port(name) for name in DataAssets.ports[0:3]]
  for port in ports:
    for dest in ports:
      if dest != port:
        port.newDestination(dest)
    for _ in range(8):
      port.newRandomCargo()
  
  ports[0].pos = [465,175]
  ports[1].pos = [880,845]
  ports[2].pos = [1688,157]
  # for i in range(len(ports)):
    # ports[i].pos = [islands[i].pos[0]+70, islands[i].pos[1]+20]
  log("[DONE]")

  log("Building ferries...")
  ferries: Ferry = [Ferry()]
  ferries[0].destination = ports[0]
  ferries[0].arrive()
  log("[DONE]")
  
  log("Building UIs...")
  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()
  cargoMenu = CargoSelect()
  destMenu = DestinationSelect()
  worldMap = WorldMap()
  worldMap.ports = ports
  worldMap.ferries = ferries
  worldMap.selection = ports[0]
  # worldMap.islands = islands
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
      if event.key == pg.K_m:
        gameState = "cargoMenu"

      if gameState == "cargoMenu":
        ferry = worldMap.selection.ferries[0] if worldMap.selection.ferries else None
        gameState = cargoMenu.processKeypress(event.key, worldMap.selection, ferry)

      elif gameState == "destMenu":
        ferry = worldMap.selection.ferries[0] if worldMap.selection.ferries else None
        gameState = destMenu.processKeypress(event.key, worldMap.selection, ferry)

      elif gameState == "startMenu":
        gameState = startMenu.processKeypress(event.key)

      elif gameState == "game":
        gameState = worldMap.processKeypress(event.key)

    # update screen
    if gameState == "cargoMenu":
      screen.fill((1,42,74))
      ferry = worldMap.selection.ferries[0] if worldMap.selection.ferries else None
      cargoMenu.draw(worldMap.selection, ferry)
    elif gameState == "destMenu":
      screen.fill((1,42,74))
      ferry = worldMap.selection.ferries[0] if worldMap.selection.ferries else None
      destMenu.draw(worldMap.selection, ferry)
    elif gameState == "startMenu":
      screen.fill((1,42,74))
      startMenu.draw()
    elif gameState == "game":
      # screen.fill((1,73,124))
      worldMap.draw()
      creditsDisplay.draw()
    elif gameState == "quit":
        running = False

    pg.display.flip()

    clock.tick(30) / 1000
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
            creditsDisplay.credits += ferry.arrive()

  pg.quit()


main_dir = os.path.split(os.path.abspath(__file__))[0]
assetDir = os.path.join(main_dir, "assets")

main()