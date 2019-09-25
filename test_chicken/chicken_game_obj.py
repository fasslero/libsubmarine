import argparse
import json
import logging
import sys
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

from test_chicken.test_utils import keccak_256_encript_uint32

CHAIN_ID = 3    # mainNet = 1 | Ropsten = 3 | Rinkeby = 4 | Goerli = 5 | Kovan = 42
BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"
log = logging.getLogger('SubmarineCommitGenerator')


def _get_args():
    '''
    Internal function. Creates an argparser for the main method to use.

    :return: parser: argparse object for parsing program arguments.
    '''
    parser = argparse.ArgumentParser(
        description=
        "Deploy chicken game contract needs -i infura_address, -k private key, "
        "-g gas amount (optional), -gp gas price (optional)",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-i',
        '--infura',
        required=True,
        type=str,
        default="")
    parser.add_argument(
        '-k',
        '--private_key',
        required=True,
        type=str,
        default="")
    parser.add_argument(
        '-g',
        '--gas',
        required=False,
        type=int,
        default=6092664)
    parser.add_argument(
        '-gp',
        '--gas_price',
        required=False,
        type=str,
        default="21",
        help="Gas price in Gwei")
    return parser.parse_args()


class ChickenGame:

    def __init__(self, infura, private_key, gas, gas_price, game_json_path):
        self.gas = gas
        self.gas_price = gas_price
        self.w3 = Web3(HTTPProvider(infura))
        assert self.w3.isConnected(), f"Connection problem to infura at {infura}"
        self.owner_account = self.w3.eth.account.privateKeyToAccount(private_key)
        # compile your smart contract with truffle first
        truffleFile = json.load(open(game_json_path))
        self.abi = truffleFile['abi']
        self.bytecode = truffleFile['bytecode']
        self.contract = self.w3.eth.contract(bytecode=self.bytecode, abi=self.abi)
        self.tx_hash = None
        self.tx_receipt = None
        self.init_tx_receipt = None
        self.select_winner_tx_receipt = None
        self.contract_transaction = None
        self.contract_block_number = None

    ########################
    # Contract game transactions
    ########################
    def deploy_game_contract(self):
        """
        Deploy chicken game contract to a test net
        :param infura: infura private url
        :param private_key: contract owner private key
        :param gas:
        :param gas_price:
        :return:
        """

        # building transaction
        construct_txn = self.contract.constructor().buildTransaction({
            'from': self.owner_account.address,
            'nonce': self.w3.eth.getTransactionCount(self.owner_account.address),
            'gas': self.gas,
            'gasPrice': self.w3.toWei(self.gas_price, 'gwei')})

        signed = self.owner_account.signTransaction(construct_txn)

        self.tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        log.info(f"game hash is: {self.tx_hash.hex()}")
        self.tx_receipt = self.w3.eth.waitForTransactionReceipt(self.tx_hash, timeout=720)
        assert self.tx_receipt.status == 1, \
            f"{self.tx_hash.hex()} failed, receipt status should be 1, please check on etherscan.io"

        log.info(f"Contract Deployed At: {self.tx_receipt['contractAddress']}")
        self.contract = self.w3.eth.contract(address=self.tx_receipt['contractAddress'],
                                             bytecode=self.bytecode,
                                             abi=self.abi)

        contract_data = {"address": self.contract.address,
                         "bytecode": self.contract.bytecode.hex(),
                         "abi": list(self.contract.abi)}
        file_name = f"../contracts/deployed_contracts/{self.contract.address}.json"
        log.info(f"write contract data to file {file_name}")
        with open(file_name, 'w+') as json_file:
            json.dump(contract_data, json_file)

    def init_chicken_game(self, start_block, start_reveal_block, min_bet, end_commit_block):
        """
        Init the game contract with the params
        distance from start block to start reveal block is max 256
        min bet is in Wei
        """
        end_commit_block_crypt = keccak_256_encript_uint32(end_commit_block)
        nonce = self.w3.eth.getTransactionCount(self.owner_account.address)

        log.info(f"init chicken game")
        tx_dict = self.contract.functions.initChickenGame(
            start_block, start_reveal_block, min_bet, end_commit_block_crypt).\
            buildTransaction({
                            'chainId': CHAIN_ID,
                            'gas': self.gas,
                            'gasPrice': self.w3.toWei(self.gas_price, 'gwei'),
                            'nonce': nonce})

        signed_tx = self.owner_account.signTransaction(tx_dict)
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        self.init_tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=720)

        log.info(f"Init game tx receipt is {self.init_tx_receipt}")
        return self.init_tx_receipt

    def select_winner(self, end_commit_block):
        """
        call select winner function of game contract
        end_commit_block is the decrypted end commit block as provided in the init function
        """
        nonce = self.w3.eth.getTransactionCount(self.owner_account.address)

        tx_dict = self.contract.functions.selectWinner(end_commit_block).\
            buildTransaction({
                              'chainId': CHAIN_ID,
                              'gas': self.gas,
                              'gasPrice': self.w3.toWei(self.gas_price, 'gwei'),
                              'nonce': nonce})

        log.info(f"Select winner transaction")
        signed_tx = self.owner_account.signTransaction(tx_dict)
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        self.select_winner_tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=720)

        log.info(f"Select winner tx receipt is {self.select_winner_tx_receipt}")
        return self.select_winner_tx_receipt

    #################
    # CONTRACT CALLS
    #################

    def get_manager(self):
        return self.contract.functions.manager().call()

    def get_min_bet(self):
        return self.contract.functions.minBet().call()

    def get_start_block(self):
        return self.contract.functions.startBlock().call()

    def get_start_reveal_block(self):
        return self.contract.functions.startRevealBlock().call()

    def get_end_reveal_block(self):
        return self.contract.functions.endRevealBlock().call()

    def get_end_commit_block(self):
        return self.contract.functions.endCommitBlock().call()

    def get_end_commit_block_crypt(self):
        return self.contract.functions.endCommitBlockCrypt().call()

    def get_is_contract_initiated(self):
        return self.contract.functions.isInitiated().call()

    def get_winner_selected(self):
        return self.contract.functions.winnerSelected().call()

    def get_winning_submarine_id(self):
        return self.contract.functions.winningSubmarineId().call()


def main():
    parser = _get_args()
    infura = parser.infura
    private_key = parser.private_key
    gas = parser.gas
    gas_price = parser.gas_price

    game_obj = ChickenGame(infura, private_key, gas, gas_price)
    game_obj.deploy_game_contract()

    return game_obj.contract

    # Contract Deployed At: 0xe283efD1A9D6942E0fe9d1C69957f58ADB216ae4  --- out of gas

    # Contract Deployed At: 0x7844833c5f037B26Be9A8d21982756D744F1ff0d


if __name__ == "__main__":
    main()
