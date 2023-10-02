loglevel = 2 # 0=none  1=error 2=info

def log(message, level = 2):
  if loglevel >= level:
    match level:
      case 1: print("[  ERROR  ]", message)
      case 2: print("[  INFO   ]", message)

