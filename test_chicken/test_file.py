from time import sleep
import json
import logbook
import os
from pathlib import Path
from test_chicken.chicken_game_obj import ChickenGame
from test_chicken.chicken_player import Player

BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"
game_json = '../contracts/compiled_contracts/ChickenSubmarine.json'
_logger = logbook.Logger(__name__)


script_dir = os.path.dirname(__file__)
game_json_path = os.path.abspath(game_json)
path = Path(script_dir, game_json)
print(str(path))
try:
    truffleFile = json.load(open(game_json_path))
    game_address = truffleFile.get('contract_address')
    #print(truffleFile)
except Exception:
    print(f"{game_json_path} is no good")