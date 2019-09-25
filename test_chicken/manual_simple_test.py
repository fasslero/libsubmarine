import sys
from time import sleep

import logging
import os
from test_chicken.chicken_game_obj import ChickenGame
from test_chicken.chicken_player import Player

#BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
BORIS_INFURA = "https://ropsten.infura.io/v3/a7c4034638a64a87a0846d19bc765385"
#OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
OFER_INFURA = "https://ropsten.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"
game_json = '../contracts/compiled_contracts/ChickenSubmarine.json'
# Logging

log = logging.getLogger('SubmarineCommitGenerator')

game_json_path = os.path.abspath(game_json)


def create_game():
    game = ChickenGame(BORIS_INFURA, BORIS_KEY, 6092664, 21, game_json_path)
    print(f"Created a chicken game obj {game}")
    return game


def create_ofer_player(game):
    player_ofer = Player(OFER_KEY, infura_url=OFER_INFURA, game_obj=game)
    log.info(f"Created Player {player_ofer}")

    return player_ofer


def create_boris_player(game):
    player_boris = Player(BORIS_KEY, infura_url=BORIS_INFURA, game_obj=game)
    log.info(f"Created Player {player_boris}")
    return player_boris


def wait_for_block(game, block_number, massage):
    while game.w3.eth.blockNumber <= block_number:
        log.info(f"{massage} - current block {game.w3.eth.blockNumber} wait for block {block_number}")
        sleep(2)


def basic_positive_flow():
    game = create_game()
    ofer_bet = 50000000000
    boris_bet = 150000000000

    log.info(f"Created a chicken game obj {game.__repr__()}")

    game.deploy_game_contract()
    log.info(f"Deployed the contract to the network, game address is {game.contract.address}")

    current_block = game.w3.eth.blockNumber
    log.info(f"Current block number is {current_block}")

    start_block = current_block + 10
    end_commit_block = start_block + 15
    start_reveal_block = end_commit_block + 2

    res = game.init_chicken_game(start_block=start_block,
                                 start_reveal_block=start_reveal_block,
                                 min_bet=100,
                                 end_commit_block=end_commit_block)
    log.info(f"init the contract, result is {res}")

    ofer_player = create_ofer_player(game)
    boris_player = create_boris_player(game)

    wait_for_block(game, start_block, "wait for game to start")

    boris_current_block = game.w3.eth.blockNumber
    log.info(f"Create submarine with Boris's bet of {boris_bet} on block {boris_current_block}")
    boris_bet_res = boris_player.send_ether_to_submarine(boris_bet)
    log.info(f"boris bet res is {boris_bet_res} at block num ~ {boris_current_block}")

    current_block = game.w3.eth.blockNumber
    wait_for_block(game, current_block + 1, "Wait for one block to separate the bets")

    ofer_current_block = game.w3.eth.blockNumber
    log.info(f"Create submarine with ofer's bet of {ofer_bet} on block {ofer_current_block}")
    ofer_bet_res = ofer_player.send_ether_to_submarine(ofer_bet)
    log.info(f"Ofer bet res is {ofer_bet_res} at block num ~ {ofer_current_block}")

    # wait for reveal period
    start_reveal_period = game.get_start_reveal_block()
    wait_for_block(game, start_reveal_period, "Wait for reveal period to start")

    # reveal the players
    log.info(f"Reveal Boris player")
    boris_reveal_res = boris_player.submarine_reveal_and_unlock()
    log.info(f"Reveal Ofer player")
    ofer_reveal_res = ofer_player.submarine_reveal_and_unlock()

    log.info(f"Boris reveal and unlock result: {boris_reveal_res}")
    log.info(f"Ofer reveal and unlock result: {ofer_reveal_res}")

    # choose winner
    wait_for_block(game, game.get_end_reveal_block() + 1, "wait for end reveal block + 1")
    res = game.select_winner(end_commit_block)
    log.info(f"Select winner ended with {res}")

    # now finalize the game by the two players
    ofer_finalize_res = ofer_player.finalize()
    boris_finalize_res = boris_player.finalize()
    log.info(f"Ofer finalize game ended with {ofer_finalize_res}")
    log.info(f"Boris finalize game ended with {boris_finalize_res}")

    # todo - add details about the two players and the manager (amount of eth etc.)


if __name__ == "__main__":
    basic_positive_flow()
