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

def genWorld():
  from matplotlib import pyplot as plt
  from PIL import Image
  import numpy as np
  #brown, green, blue, grey, assorted
  colors = [[[88, 47, 14],[127, 79, 36],[147, 102, 57],[166, 138, 100],[182, 173, 144]],\
         [[51, 61, 41],[65, 72, 51],[101, 109, 74],[164, 172, 134],[194, 197, 170]],\
         [[1, 42, 74],[1, 73, 124],[44, 125, 160],[97, 165, 194],[169, 214, 229]],\
         [[33, 37, 41],[73, 80, 87],[108, 117, 125],[206, 212, 218],[233, 236, 239]],\
         [[10, 9, 8],[241, 143, 1],[204, 41, 54],[69, 203, 100],[94, 80, 63]]]
  
  rando = np.random.randint(5, size=(1000,1000))

  height = 500
  width = 500
  def numAdj(arr, x, y):
    count = 0
    for row in arr[max(0,y-1):min(len(arr),y+2)]:
      count += sum(row[max(0,x-1):min(len(arr[0]),x+2)])
    return count
  while True:
    world = np.random.randint(2, size=(height//10,width//10))

    # islandCenters = [[rand(0,height), rand(0,width)] for _ in range(4)]
    # islandRadius = [rand(5,20) for _ in range(4)]
    # for i in range(4):
    #   for y in range(max(0, islandCenters[i][0]-islandRadius[i]),min(len(world), islandCenters[i][0]+islandRadius[i])):
    #     for x in range(max(0, islandCenters[i][1]-islandRadius[i]),min(len(world[0]), islandCenters[i][1]+islandRadius[i])):
    #       world[y][x] = 1

    plt.imshow(world)
    plt.show()


    # for _ in range(1):
    #   for y, row in enumerate(world):
    #     for x, col in enumerate(row):
    #       if numAdj(world, x, y) < 4:
    #         world[y][x] = 0

    for _ in range(1):
      for y, row in enumerate(world):
        for x, col in enumerate(row):
          if numAdj(world, x, y) < 5:
            world[y][x] = 0

    plt.imshow(world)
    plt.show()

    new = []

    for y, row in enumerate(world):
      temp = []
      for x, col in enumerate(row):
        temp.extend([col]*2)
      for _ in range(2): new.append(temp)

    world = np.array(new)
    plt.imshow(world)
    plt.show()
    for y, row in enumerate(world):
      for x, col in enumerate(row):
        if rand(0,2) == 1:
          world[y][x] = world[y][x] -1

    plt.imshow(world)
    plt.show()

    for _ in range(1):
      for y, row in enumerate(world):
        for x, col in enumerate(row):
          if numAdj(world, x, y) < 5:
            world[y][x] = 0
        

    plt.imshow(world)
    plt.show()

    map = np.zeros((height,width,3))
    for y, row in enumerate(world):
      for x, col in enumerate(row):
        if col == 0:
          map[y][x] = [44, 125, 160]
          continue
        map[y][x] = [0, 128, 0]
    img = Image.fromarray(map.astype(np.uint8))
    img.save("name.png")
  # while True:
  #   continue
  return

def main():
  genWorld()
  return

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