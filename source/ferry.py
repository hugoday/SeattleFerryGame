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

  log("Building ports...")
  ports = [Port(name) for name in DataAssets.ports[0:3]]
  for port in ports:
    for dest in ports:
      if dest != port:
        port.newDestination(dest)
    for _ in range(8):
      port.newRandomCargo()
  
  ports[0].pos = [100,200]
  ports[1].pos = [400,200]
  ports[2].pos = [300,300]
  log("[DONE]")

  log("Building ferries...")
  ferries: Ferry = [Ferry(ports[0])]
  ferries[0].pos = [ports[0].pos[0], ports[0].pos[1] + 10]
  log("[DONE]")
  
  log("Building UIs...")
  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()
  cargoMenu = CargoSelect()
  destMenu = DestinationSelect()
  worldMap = WorldMap()
  worldMap.ports = ports
  worldMap.ferries = ferries
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
        gameState = cargoMenu.processKeypress(event.key, ferries[0].port, ferries[0])
        
      elif gameState == "destMenu":
        gameState = destMenu.processKeypress(event.key, ferries[0].port, ferries[0])
        
      elif gameState == "startMenu":
       gameState = startMenu.processKeypress(event.key)

      elif gameState == "game":
        for ferry in ferries:
          if ferry.distanceFromDest == 0:
            gameState = "cargoMenu"

    # update screen
    if gameState == "cargoMenu":
      screen.fill((1,42,74))
      cargoMenu.draw(ferries[0].port, ferries[0])
    elif gameState == "destMenu":
      screen.fill((1,42,74))
      destMenu.draw(ferries[0].port, ferries[0])
    elif gameState == "startMenu":
      screen.fill((1,42,74))
      startMenu.draw()
    elif gameState == "game":
      screen.fill((1,73,124))
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