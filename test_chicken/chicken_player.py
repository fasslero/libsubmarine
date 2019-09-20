import json
import logging
import sys
import time

import logbook as logbook
import rlp
from ethereum import transactions
from ethereum.utils import normalize_address
from web3 import Web3, HTTPProvider

from generate_commitment.generate_submarine_commit import generateCommitAddress
from test_chicken.test_utils import keccak_256_encript_uint32, generate_proof_blob, rec_bin, rec_hex

OURGASLIMIT = 8000000
BASIC_SEND_GAS_LIMIT = OURGASLIMIT
REVEAL_GAS_LIMIT = OURGASLIMIT
SELECT_WIN_GAS_LIMIT = OURGASLIMIT
FINALIZE_GAS_LIMIT = OURGASLIMIT
CHAIN_ID = 3    # mainNet = 1 | Ropsten = 3 | Rinkeby = 4 | Goerli = 5 | Kovan = 42

log = logging.getLogger('SubmarineCommitGenerator')

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

    def __init__(self, private_key, infura_url, game_obj):
        self.private_key = private_key
        self.w3 = Web3(HTTPProvider(infura_url))
        assert self.w3.isConnected(), f"Infura connection problem at {infura_url}"
        self.user_account = self.w3.eth.account.privateKeyToAccount(self.private_key)
        self.ourgasprice = 50000000000
        self.submarine_basic_cash = 250000000000000000
        self.game_obj = game_obj
        self.game_contract = game_obj.contract
        self.game_address = game_obj.contract.address
        self.submarin_address_b = None
        self.submarine_commit = None
        self.submarine_witness = None
        self.submarine_unlock_tx = None
        self.submarine_tx_receipt = None
        self.reveal_tx_receipt = None
        self.bet_amount_in_wei = None

    ############################
    # Player functions
    ############################

    def send_ether_to_submarine(self, amount_in_wei):
        """
        generate submarine commitment to the game contract with the amount_in_wei bet.
        sent the submarine transaction to the generated sub address
        stores the submarine and the trans receipt
        """

        self.submarin_address_b, self.submarine_commit, self.submarine_witness, self.submarine_unlock_tx = \
            generateCommitAddress(rec_bin(self.user_account.address),
                                  rec_bin(self.game_address),
                                  amount_in_wei, b"",
                                  self.ourgasprice, BASIC_SEND_GAS_LIMIT)

        # Save for the reveal
        self.bet_amount_in_wei = amount_in_wei
        self.submarine_tx_receipt = self.send_wei_to_submarine(self.submarine_basic_cash)

        if self.submarine_tx_receipt is None:
            return {'status': 'failed', 'error': 'timeout'}
        return{'status': 'added', 'tx_receipt': self.submarine_tx_receipt}

    def submarine_reveal_and_unlock(self):
        """
        Send submarine reveal to the game contract
        """
        commit_tx_block_num = self.submarine_tx_receipt.blockNumber
        proof_blob = generate_proof_blob(self)
        self._unlock_tx_unsigned_rlp()
        nonce = self.w3.eth.getTransactionCount(self.user_account.address)

        reveal_tx_dict = self.game_contract.functions.reveal(
            commit_tx_block_num,
            b'',  # unlock extra data - we have none
            rec_bin(self.submarine_witness),
            self.unlock_tx_unsigned_rlp,
            proof_blob).\
            buildTransaction({
                              'chainId': CHAIN_ID,
                              'gas': REVEAL_GAS_LIMIT,
                              'gasPrice': self.ourgasprice * 2,
                              'nonce': nonce})

        log.info("Send reveal transaction")
        signed_reveal_tx = self.user_account.signTransaction(reveal_tx_dict)
        reveal_tx_hash = self.w3.eth.sendRawTransaction(signed_reveal_tx.rawTransaction)
        self.reveal_tx_receipt = self.w3.eth.waitForTransactionReceipt(reveal_tx_hash, timeout=720)

        if self.reveal_tx_receipt is None:
            log.info(f"Reveal transaction failed")
            return {'status': 'failed', 'error': 'timeout'}
        log.info(f"Reveal transaction was sent: {self.reveal_tx_receipt}")

        sent_flag = False
        iteration_number = 0
        while iteration_number < 4 and not sent_flag:
            try:
                log.info(f"send unlock transaction")
                unlock_tx_hash = self.w3.eth.sendRawTransaction(self.submarine_unlock_tx)
                sent_flag = True
            except ValueError as e:
                log.info(f"Unlock failed with massage: {e}")
                iteration_number += 1
                submarine_tx_receipt = self.send_wei_to_submarine(self.submarine_basic_cash)
                log.info(f"Submarine tx receipt is :{submarine_tx_receipt}")

        self.reveal_tx_receipt = self.w3.eth.waitForTransactionReceipt(unlock_tx_hash, timeout=720)
        return self.reveal_tx_receipt

    def finalize(self):
        """
        Collect reword from game contract
        call finalize on the submarine, recive the money from the game contract
        """
        nonce = self.w3.eth.getTransactionCount(self.user_account.address)
        tx_dict = self.game_contract.functions.finalize(rec_bin(self.submarine_commit)).buildTransaction({
            'chainId': CHAIN_ID,
            'gas': FINALIZE_GAS_LIMIT,
            'gasPrice': self.ourgasprice,
            'nonce': nonce,
        })

        signed_tx = self.user_account.signTransaction(tx_dict)
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=720)

        if tx_receipt is None:
            log.info("finalize call failed")
        log.info({'status': 'added', 'processed_receipt': tx_receipt})

    def _unlock_tx_unsigned_rlp(self):
        unlock_tx_info = rlp.decode(rec_bin(self.submarine_unlock_tx))
        log.info(f"Unlock tx hex object: {rec_hex(unlock_tx_info)}")

        self.unlock_tx_unsigned_object = transactions.UnsignedTransaction(
            int.from_bytes(unlock_tx_info[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_info[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_info[2], byteorder="big"),  # startgas
            unlock_tx_info[3],  # to addr
            int.from_bytes(unlock_tx_info[4], byteorder="big"),  # value
            unlock_tx_info[5],  # data
        )

        self.unlock_tx_unsigned_rlp = rlp.encode(self.unlock_tx_unsigned_object, transactions.UnsignedTransaction)

    def send_wei_to_submarine(self, amount_in_wei):
        tx_dict = {
            'to': rec_bin(self.submarin_address_b),
            'value': amount_in_wei,
            'gas': BASIC_SEND_GAS_LIMIT,
            'gasPrice': self.ourgasprice,
            'nonce': self.w3.eth.getTransactionCount(self.user_account.address),
            'chainId': CHAIN_ID
        }

        signed_tx = self.user_account.signTransaction(tx_dict)
        log.info(f"Send {amount_in_wei} wei to submarine {self.submarin_address_b}")
        tx_hash = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=720)
