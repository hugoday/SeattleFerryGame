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

def genScene():
  rnd.seed() #5
  width = 100
  height = 50
  scene = []
  shore = 15
  docksH = (rnd.randint(5, 24),rnd.randint(24, 45))
  docks = [Dock(name, [docksH[i], 0]) for i, name in enumerate(["North", "South"])]
  dock = 0
  for h in range(height):
    line = []
    shore = abs(shore)
    if h in docksH:
      line.extend('l'*(shore-8)+str(docks[dock].name)+'d'*12+'w'*(width-shore-10))
      docks[dock].pos[1] = shore - 8
      dock += 1
    else:
      line.extend('l'*(shore-1)+'s'+'w'*(width-shore-1))
    scene.append(line)
    shore += rnd.randint(-1, 1)
  return (scene, docks)


def main():
  pg.init()
  font = pg.font.SysFont("consolas", 18)
  screenWidth = 640
  screenHeight = 480
  screen = pg.display.set_mode((screenWidth, screenHeight))
  clock = pg.time.Clock()
  running = True
  gameState = "startMenu"

  time = 0
  frames = 1

  # if True:
  #   import matplotlib.image as mplimg
  #   mplimg.imsave('name.png', [[[255,0,0],(0,255,0)]])

  log("Building docks...")
  docks = [Dock(name) for name in DataAssets.ports[0:2]]
  for dock in docks:
    for dest in docks:
      if dest != dock:
        dock.newDestination(dest)
    for _ in range(8):
      dock.newRandomCargo()
  
  docks[0].pos = [100,200]
  docks[1].pos = [400,200]
  log("[DONE]")

  log("Building ferries...")
  ferries = [Ferry(docks[0])]
  ferries[0].pos = [docks[0].pos[0], docks[0].pos[1] + 10]
  log("[DONE]")
  
  log("Building UIs...")
  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()
  cargoMenu = CargoSelect()
  destMenu = DestinationSelect()
  worldMap = WorldMap()
  worldMap.docks = docks
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
        gameState = cargoMenu.processKeypress(event.key, docks[0], ferries[0])
        
      elif gameState == "destMenu":
        gameState = destMenu.processKeypress(event.key, docks[0], ferries[0])
        
      elif gameState == "startMenu":
       gameState = startMenu.processKeypress(event.key)

      elif gameState == "game":
        for ferry in ferries:
          if ferry.distanceFromDest == 0:
            gameState = cargoMenu

        

    # update screen
    if gameState == "cargoMenu":
      screen.fill((0,0,0))
      cargoMenu.draw(docks[0], ferries[0])
    elif gameState == "destMenu":
      screen.fill((0,0,0))
      destMenu.draw(docks[0], ferries[0])
    elif gameState == "startMenu":
      screen.fill((0,0,0))
      startMenu.draw()
    elif gameState == "game":
      screen.blit(background, (0, 0))
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
          print(ferry.distanceFromDest)
          ferry.update()


pg.quit()


main_dir = os.path.split(os.path.abspath(__file__))[0]
assetDir = os.path.join(main_dir, "assets")

main()