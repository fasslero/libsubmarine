from time import sleep

import logbook
import os
from test_chicken.chicken_game_obj import ChickenGame
from test_chicken.chicken_player import Player

BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"
game_json = '../contracts/compiled_contracts/ChickenSubmarine.json'
_logger = logbook.Logger(__name__)

game_json_path = os.path.abspath(game_json)


def create_game():
    game = ChickenGame(OFER_INFURA, OFER_KEY, 6092664, 21, game_json_path)
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


def create_ofer_player(game):
    player_ofer = Player(OFER_KEY, infura_url=OFER_INFURA, game_obj=game)
    _logger.debug(f"Created Player {player_ofer}")

    return player_ofer


def create_boris_player(game):
    player_boris = Player(BORIS_KEY, infura_url=OFER_INFURA, game_obj=game)
    _logger.debug(f"Created Player {player_boris}")
    return player_boris


def basic_positive_flow():
    game = create_game()
    ofer_bet = 1000000
    boris_bet = 2000000

    _logger.info(f"Created a chicken game obj {game}")

    game.deploy_game_contract()
    _logger.info(f"Deployed the contract to the network, game address is {game.contract.address}")

    current_block = game.w3.eth.blockNumber
    _logger.info(f"Current block number is {current_block}")

    end_commit_block = current_block + 40
    res = game.init_chicken_game(start_block=current_block + 10,
                                 start_reveal_block=current_block + 50,
                                 min_bet=100,
                                 end_commit_block=end_commit_block)
    _logger.info(f"init the contract, result is {res}")

    ofer_player = create_ofer_player(game)
    boris_player = create_boris_player(game)

    _logger.info("Sleep for 15 seconds")
    sleep(15)

    _logger.info(f"Create submarine with ofer's bet of {ofer_bet}")
    ofer_current_block = game.w3.eth.blockNumber
    ofer_bet_res = ofer_player.send_ether_to_submarine(ofer_bet)
    _logger.info(f"Ofer bet res is {ofer_bet_res} at block num ~ {ofer_current_block}")

    _logger.debug("Sleep for 5 seconds")
    sleep(5)

    _logger.info(f"Create submarine with Boris's bet of {boris_bet}")
    boris_current_block = game.w3.eth.blockNumber
    boris_bet_res = ofer_player.send_ether_to_submarine(boris_bet)
    _logger.info(f"boris bet res is {boris_bet_res} at block num ~ {boris_current_block}")

    # wait for reveal period
    _logger.info("Wait for reveal period to start")
    start_reveal_period = game.get_start_reveal_block()
    while game.w3.eth.blockNumber < start_reveal_period:
        _logger.info(f"current block {game.w3.eth.blockNumber} is before start reveal block {start_reveal_period}")
        sleep(1)

    # reveal the players
    try:
        _logger.info(f"Reveal both players")
        boris_reveal_res = boris_player.submarine_reveal_and_unlock()
        ofer_reveal_res = ofer_player.submarine_reveal_and_unlock()
    except Exception:
        print("Need to add block numbers")


    _logger.debug(f"Boris reveal and unlock result: {boris_reveal_res}")
    _logger.debug(f"Ofer reveal and unlock result: {ofer_reveal_res}")

    # choose winner
    res = game.select_winner(end_commit_block)
    _logger.info(f"Select winner ended with {res}")

    # now finalize the game by the two players
    ofer_finalize_res = ofer_player.finalize()
    boris_finalize_res = boris_player.finalize()
    _logger.info(f"Ofer finalize game ended with {ofer_finalize_res}")
    _logger.info(f"Boris finalize game ended with {boris_finalize_res}")

    # todo - add details about the two players and the manager (amount of eth etc.)


if __name__ == "__main__":
    basic_positive_flow()

