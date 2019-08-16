import json
import time

from web3 import Web3, HTTPProvider

from test.test_utils import keccak_256_encript_uint32

OURGASLIMIT = 3712394
OURGASPRICE = 10**6
BASIC_SEND_GAS_LIMIT = 21000
REVEAL_GAS_LIMIT = 400000
SELECT_WIN_GAS_LIMIT = 400000
FINALIZE_GAS_LIMIT = 100000
CHAIN_ID = 42    # mainNet = 1 | Ropsten = 3 | Rinkeby = 4 | Goerli = 5 | Kovan = 42

# web3.py instance
w3 = Web3(HTTPProvider("https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"))
print(w3.isConnected())


#private_key = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a" #"<Private Key here with 0x prefix>"
user_account = w3.eth.account.privateKeyToAccount(private_key)

#wallet_private_key = [WALLET_PRIVATE_KEY]
#wallet_address = [WALLET_ADDRESS]

# load deployed contract
truffleFile = json.load(open('../contracts/deployed_contracts/ChickenSubmarine.json'))
abi = truffleFile['abi']
bytecode = truffleFile['bytecode']
contract_address = truffleFile['address']
contract = w3.eth.contract(address=contract_address,bytecode=bytecode, abi=abi)
#contract_ = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])

############################
# Player functions
############################
def send_ether_to_submarine(amount_in_wei):
    """
    generate submarine commitment to the game contract with the amount_in_wei bet.
    sent the submarine transaction to the generated sub address
    stores the submarine and the trans receipt
    """
    nonce = w3.eth.getTransactionCount(user_account.address)

    tx_dict = {
        'to': contract_address,
        'value': amount_in_wei,
        'gas': BASIC_SEND_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
        'chainId': CHAIN_ID
    }

    signed_tx = user_account.signTransaction(tx_dict)

    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)

    tx_receipt = None
    count = 0
    while tx_receipt is None and (count < 30):
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        print(tx_receipt)
        time.sleep(10)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return{'status': 'added', 'tx_receipt': tx_receipt}



def submarine_reveal(commit_tx_block_num, witness, rlp_unlock_unsigned_tx, proof_blob):
    """
    Send submarine reveal to the game contract
    """
    nonce = w3.eth.getTransactionCount(user_account.address)

    tx_dict = contract.functions.reveal(commit_tx_block_num, b'', witness, rlp_unlock_unsigned_tx, proof_blob).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': REVEAL_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = user_account.signTransaction(tx_dict)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


def finalize(submarine_id):
    """
    Collect reword from game contract
    call finalize on the submarine, recive the money from the game contract
    """
    nonce = w3.eth.getTransactionCount(user_account.address)

    tx_dict = contract.functions.finalize(submarine_id).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': FINALIZE_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = user_account.signTransaction(tx_dict)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)

    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


########################
## Contract game transactions
########################
def init_chicken_game(start_block, start_reveal_block, min_bet, end_commit_block):
    """
    Init the game contract with the params
    distance from start block to start reveal block is max 256
    """
    end_commit_block_crypt = keccak_256_encript_uint32(end_commit_block)
    nonce = w3.eth.getTransactionCount(user_account.address)
    tx_dict = contract.functions.initChickenGame(start_block, start_reveal_block, min_bet, end_commit_block_crypt).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': REVEAL_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = user_account.signTransaction(tx_dict)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)

    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


def select_winner(end_commit_block):
    """
    call select winner function of game contract
    end_commit_block is the decrypted end commit block as provided in the init function
    """
    nonce = w3.eth.getTransactionCount(user_account.address)

    tx_dict = contract.functions.selectWinner(end_commit_block).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': SELECT_WIN_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = user_account.signTransaction(tx_dict)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}



#################
## CONTRACT CALLS
#################
def get_manager():
    return contract.functions.manager().call()


def get_min_bet():
    return contract.functions.minBet().call()


def get_start_block():
    return contract.functions.startBlock().call()


def get_start_reveal_block():
    return contract.functions.startRevealBlock().call()


def get_end_reveal_block():
    return contract.functions.endRevealBlock().call()


def get_end_commit_block():
    return contract.functions.endCommitBlock().call()


def get_end_commit_block_crypt():
    return contract.functions.endCommitBlockCrypt().call()


def get_is_contract_initiated():
    return contract.functions.isInitiated().call()


def get_winner_selected():
    return contract.functions.winnerSelected().cal()


def get_winning_submarine_id():
    return contract.functions.winningSubmarineId().call()