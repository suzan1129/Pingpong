import sys
from os import path
sys.path.append(path.dirname(__file__))
from src.game import PingPong


GAME_SETUP = {
    "game": PingPong
}
