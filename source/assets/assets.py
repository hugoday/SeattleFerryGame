class StaticAssets():
  markers = [[".:.","\0|\0"],["\0[:]\0","[___]"],\
            ["\0[o]\0","\0|X|\0","[___]"],\
            ["\0[X]\0", "\0/|\\\0", "/\0|\0\\"],\
            ["\0\04_Y\0\0", "_[|\\0|]_", "/\0|\0|\0\\"]]
  markerSizes = [(2,3),(3,5),(3,5),(3,7)]

class UiAssets():
  startMenu = ["Welcome to Seattle Ferrys","Press any key to continue"]
  cargoSelect = ["Cargo selection screen here"]
  destinationSelect = ["Destination selection screen here"]
  
class DataAssets():
  cargoContents = ["Salmon", "Bikes", "Wine", "Camping gear", "Boat parts",\
                "Cat food", "Granola", "Hot peppers", "SCUBA gear", "Avocados",\
                "Pasta", "Hard seltzers", "Guiness", ]
  ports = ["Mercer Island", "Edmonds", "Kingston", "Bainbridge Island"]


# class Colors():
#   def __init__(self):
#     global LAND
#     global SHORE
#     global WATER
#     global DOCKWOOD
#     global DOCKNAME

#     cr.start_color()
#     cr.init_pair(1, 22, cr.COLOR_GREEN)
#     cr.init_pair(2, 255, 220)
#     cr.init_pair(3, 27, 20)
#     cr.init_pair(4, 0, 52)
#     cr.init_pair(5, 255, 240)

#     LAND = cr.color_pair(1)
#     SHORE = cr.color_pair(2)
#     WATER = cr.color_pair(3)
#     DOCKWOOD = cr.color_pair(4)
#     DOCKNAME = cr.color_pair(5)