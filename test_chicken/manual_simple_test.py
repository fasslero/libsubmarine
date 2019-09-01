from time import sleep

from test_chicken.chicken_game_obj import ChickenGame
from test_chicken.chicken_player import Player

BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"
game_json = './contracts/compiled_contracts/ChickenSubmarine.json'


def create_game():
    game = ChickenGame(OFER_INFURA, OFER_KEY, 6092664, 21)
    print(f"Created a chicken game obj {game}")
    return game


def deploy_game(game):
    game.deploy_game_contract()
    print(f"Deployed the contract to the network, game address is {game.contract.address}")


def init_game(game):
    current_block = game.w3.eth.blockNumber
    print(f"Current block number is {current_block}")
    end_commit_block = current_block + 40
    res = game.init_chicken_game(start_block=current_block + 10,
                                 start_reveal_block=current_block + 50,
                                 min_bet=100,
                                 end_commit_block=end_commit_block)
    print(f"init the contract, result is {res}")
    return res


def create_ofer_player():
    player_ofer = Player(OFER_KEY, infura_url=OFER_INFURA, game_json=game_json)
    return player_ofer


def create_boris_player():
    player_boris = Player(BORIS_KEY, infura_url=OFER_INFURA, game_json=game_json)
    return player_boris


def main():
    game = ChickenGame(OFER_INFURA, OFER_KEY, 6092664, 21)
    print(f"Created a chicken game obj {game}")
    game.deploy_game_contract()
    print(f"Deployed the contract to the network, game address is {game.contract.address}")
    current_block = game.w3.eth.blockNumber
    print(f"Current block number is {current_block}")
    end_commit_block = current_block + 40
    res = game.init_chicken_game(start_block=current_block + 10,
                                 start_reveal_block=current_block + 50,
                                 min_bet=100,
                                 end_commit_block=end_commit_block)
    print(f"init the contract, result is {res}")
    ofer_player = create_ofer_player()
    boris_player = create_boris_player()

    sleep(15)
    ofer_current_block = game.w3.eth.blockNumber
    ofer_bet_res = ofer_player.send_ether_to_submarine(1000000)
    print(f"Ofer bet res is {ofer_bet_res} at block num ~ {ofer_current_block}")
    sleep(5)
    boris_current_block = game.w3.eth.blockNumber
    boris_bet_res = ofer_player.send_ether_to_submarine(1000000)
    print(f"boris bet res is {boris_bet_res} at block num ~ {boris_current_block}")

    # wait for reveal period
    start_reveal_period = game.get_start_reveal_block()
    while game.w3.eth.blockNumber < start_reveal_period:
        print(f"current block {game.w3.eth.blockNumber} is before start reveal block {start_reveal_period}")

    # reveal the players
    boris_reveal_res = boris_player.submarine_reveal()
    # choose winner
    res = game.select_winner(end_commit_block)
    print(f"Select winner ended with {res}")

    # now finalize the game

if __name__ == "__main__":
    main()

