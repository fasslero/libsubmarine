import json
import time

from web3 import Web3, HTTPProvider

from generate_commitment.generate_submarine_commit import generateCommitAddress
from test_chicken.test_utils import keccak_256_encript_uint32, generate_proof_blob

OURGASLIMIT = 3712394
OURGASPRICE = 10**9
BASIC_SEND_GAS_LIMIT = 21000
REVEAL_GAS_LIMIT = 1000000
SELECT_WIN_GAS_LIMIT = 4000000
FINALIZE_GAS_LIMIT = 1000000
CHAIN_ID = 42    # mainNet = 1 | Ropsten = 3 | Rinkeby = 4 | Goerli = 5 | Kovan = 42

# web3.py instance
# w3 = Web3(HTTPProvider("https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"))
# print(w3.isConnected())


# private_key = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a" #"<Private Key here with 0x prefix>"
#user_account = w3.eth.account.privateKeyToAccount(private_key)

#wallet_private_key = [WALLET_PRIVATE_KEY]
#wallet_address = [WALLET_ADDRESS]

# load deployed contract
# truffleFile = json.load(open('../contracts/deployed_contracts/ChickenSubmarine.json'))
# abi = truffleFile['abi']
# bytecode = truffleFile['bytecode']
# contract_address = truffleFile['address']
# contract = w3.eth.contract(address=contract_address, bytecode=bytecode, abi=abi)
#contract_ = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])


class Player:

    def __init__(self, private_key, infura_url, game_json):
        self.private_key = private_key
        self.w3 = Web3(HTTPProvider(infura_url))
        assert self.w3.isConnected(), f"Infura connection problem at {infura_url}"
        self.user_account = self.w3.eth.account.privateKeyToAccount(self.private_key)
        truffleFile = json.load(open(game_json))
        self.game_address = truffleFile.get('contract_address')
        self.game_contract = self.w3.eth.contract(address=self.game_address,
                                                  bytecode=truffleFile.get('bytecode'),
                                                  abi=truffleFile.get('abi'))
        self.submarin_address_b = None
        self.submarine_commit = None
        self.submarine_witness = None
        self.submarine_tx = None
        self.submarine_tx_receipt = None

    ############################
    # Player functions
    ############################

    def send_ether_to_submarine(self, amount_in_wei):
        """
        generate submarine commitment to the game contract with the amount_in_wei bet.
        sent the submarine transaction to the generated sub address
        stores the submarine and the trans receipt
        """

        self.submarin_address_b, self.submarine_commit, self.submarine_witness, self.submarine_tx = \
            generateCommitAddress(self.user_account.address,
                                  self.game_address,
                                  amount_in_wei, b"",
                                  OURGASPRICE, BASIC_SEND_GAS_LIMIT)

        nonce = self.w3.eth.getTransactionCount(self.user_account.address)

        tx_dict = {
            'to': self.submarin_address_b,
            'value': amount_in_wei,
            'gas': BASIC_SEND_GAS_LIMIT,
            'gasPrice': OURGASPRICE,
            'nonce': nonce,
            'chainId': CHAIN_ID
        }

        signed_tx = self.user_account.signTransaction(tx_dict)

        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        self.submarine_tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)

        if self.submarine_tx_receipt is None:
            return {'status': 'failed', 'error': 'timeout'}
        return{'status': 'added', 'tx_receipt': self.submarine_tx_receipt}

    def submarine_reveal(self, commit_tx_block_num, witness, rlp_unlock_unsigned_tx):
        """
        Send submarine reveal to the game contract
        """
        nonce = self.w3.eth.getTransactionCount(self.user_account.address)
        # todo - add create proof blob
        proof_blob = generate_proof_blob(self)

        tx_dict = self.game_contract.functions.reveal(
            commit_tx_block_num, b'', self.submarine_witness, self.submarine_tx, proof_blob).\
            buildTransaction({
                              'chainId': CHAIN_ID,
                              'gas': REVEAL_GAS_LIMIT,
                              'gasPrice': OURGASPRICE,
                              'nonce': nonce})

        signed_tx = self.user_account.signTransaction(tx_dict)
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)

        if tx_receipt is None:
            return {'status': 'failed', 'error': 'timeout'}
        return {'status': 'added', 'processed_receipt': tx_receipt}

    def finalize(self, submarine_id):
        """
        Collect reword from game contract
        call finalize on the submarine, recive the money from the game contract
        """
        nonce = self.w3.eth.getTransactionCount(self.user_account.address)
        # todo - change to submarine unlock function.
        #  game contract finalize is called only at the end by the manager
        tx_dict = self.game_contract.functions.finalize(submarine_id).buildTransaction({
            'chainId': CHAIN_ID,
            'gas': FINALIZE_GAS_LIMIT,
            'gasPrice': OURGASPRICE,
            'nonce': nonce,
        })

        signed_tx = self.user_account.signTransaction(tx_dict)
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)

        if tx_receipt is None:
            return {'status': 'failed', 'error': 'timeout'}
        return {'status': 'added', 'processed_receipt': tx_receipt}

