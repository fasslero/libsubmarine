import time
from web3 import Web3

OURGASLIMIT = 3712394
OURGASPRICE = 10**6
BASIC_SEND_GAS_LIMIT = 21000
REVEAL_GAS_LIMIT = 400000
SELECT_WIN_GAS_LIMIT = 400000
FINALIZE_GAS_LIMIT = 100000
CHAIN_ID = 42    # mainNet = 1 | Ropsten = 3 | Rinkeby = 4 | Goerli = 5 | Kovan = 42

web3_provider = Web3.HTTPProvider("https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af")
w3 = Web3(web3_provider)

user_account = w3.eth.account(private_key)

contract_address = [CONTRACT_ADDRESS]
wallet_private_key = [WALLET_PRIVATE_KEY]
wallet_address = [WALLET_ADDRESS]

'/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'
'/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'
'/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'
'/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'
'/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'

contract_ = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])


def send_ether_to_submarine(amount_in_wei):
    nonce = w3.eth.getTransactionCount(wallet_address)

    tx_dict = {
        'to': contract_address,
        'value': amount_in_wei,
        'gas': BASIC_SEND_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
        'chainId': CHAIN_ID
    }

    signed_tx = w3.eth.account.signTransaction(tx_dict, private_key=wallet_private_key)

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

########################
## CONTRACT TRANSACTIONS
########################
def init_chicken_game(start_block, start_reveal_block, min_bet, end_commit_block_crypt):
    nonce = w3.eth.getTransactionCount(wallet_address)

    tx_dict = contract.functions.initChickenGame(start_block, start_reveal_block, min_bet, end_commit_block_crypt).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': REVEAL_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.signTransaction(tx_dict, private_key=wallet_private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)

    count = 0
    while tx_receipt is None and (count < 30):
        time.sleep(10)
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        print(tx_receipt)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


def submarine_reveal(commit_tx_block_num, witness, rlp_unlock_unsigned_tx, proof_blob):
    nonce = w3.eth.getTransactionCount(wallet_address)

    tx_dict = contract.functions.reveal(commit_tx_block_num, b'', witness, rlp_unlock_unsigned_tx, proof_blob).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': REVEAL_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.signTransaction(tx_dict, private_key=wallet_private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)

    count = 0
    while tx_receipt is None and (count < 30):
        time.sleep(10)
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        print(tx_receipt)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


def select_winner(commit_block_num):
    nonce = w3.eth.getTransactionCount(wallet_address)

    tx_dict = contract.functions.selectWinner(commit_block_num).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': SELECT_WIN_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.signTransaction(tx_dict, private_key=wallet_private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)

    count = 0
    while tx_receipt is None and (count < 30):
        time.sleep(10)
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        print(tx_receipt)

    if tx_receipt is None:
        return {'status': 'failed', 'error': 'timeout'}
    return {'status': 'added', 'processed_receipt': tx_receipt}


def finalize(submarine_id):
    nonce = w3.eth.getTransactionCount(wallet_address)

    tx_dict = contract.functions.finalize(submarine_id).buildTransaction({
        'chainId': CHAIN_ID,
        'gas': FINALIZE_GAS_LIMIT,
        'gasPrice': OURGASPRICE,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.signTransaction(tx_dict, private_key=wallet_private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)

    count = 0
    while tx_receipt is None and (count < 30):
        time.sleep(10)
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        print(tx_receipt)

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