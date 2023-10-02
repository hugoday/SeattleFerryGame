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
  # gameState = "cargoMenu"

  time = 0

  # if True:
  #   import matplotlib.image as mplimg
  #   mplimg.imsave('name.png', [[[255,0,0],(0,255,0)]])

  startMenu = StartMenu()
  creditsDisplay = CreditsDisplay()

  docks = [Dock(name) for name in DataAssets.ports]
  for dock in docks:
    for dest in docks:
      if dest != dock:
        dock.newDestination(dest)
    for _ in range(8):
      dock.newRandomCargo()

  ferries = [Ferry(docks[0])]

  cargoMenu = CargoSelect()
  destMenu = DestinationSelect()
  worldMap = WorldMap()
  worldMap.docks = docks

  allSprites = pg.sprite.RenderPlain((ferries))
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
      allSprites.draw(screen)
      worldMap.draw()
      creditsDisplay.draw()
    elif gameState == "quit":
        running = False

    pg.display.flip()

    dt = clock.tick(30) / 1000
    for ferry in ferries:
      if ferry.moving:
        ferry.x += 1
        ferry.y += 1
        ferry.update()


pg.quit()


main_dir = os.path.split(os.path.abspath(__file__))[0]
assetDir = os.path.join(main_dir, "assets")

main()