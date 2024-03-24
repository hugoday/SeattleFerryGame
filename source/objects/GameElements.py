from logger import log
from pygame.sprite import *
import os
import pygame as pg

class GameElement(pg.sprite.Sprite):
  main_dir = os.path.split(os.path.abspath(__file__))[0]
  assetDir = os.path.join(main_dir, "..\\assets")

  def __init__(self, scr):
    log("New GameElement")
    self.position = [0,0]
    self.scr = scr

  def setPosition(self, position):
    if position[0]: self.position[0] = position[0]
    if position[1]: self.position[1] = position[1]
    log("set " + str(self) + " position to " + str(self.position))

  def getPosition(self):
    log("got " + str(self) + " position: " + str(self.position))
    return self.position

  def draw(self):
    log("drawing " + str(self) + " at position " + str(self.getPosition()))
    xpos, ypos = self.getPosition()
    for x, row in enumerate(self.image):
      for y, col in enumerate(row):
        if col == "\0":
          continue
        self.scr.addstr(xpos+x,ypos+y, col)
        pass

  def load_image(name, colorkey=None, scale=1):
    fullname = os.path.join(GameElement.assetDir, name)
    image = pg.image.load(fullname)

    size = image.get_size()
    size = (size[0] * scale, size[1] * scale)
    image = pg.transform.scale(image, size)

    image = image.convert_alpha()
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, pg.RLEACCEL)
    return image, image.get_rect()