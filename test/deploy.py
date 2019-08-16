import json
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

# web3.py instance
w3 = Web3(HTTPProvider("https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"))
print(w3.isConnected())

key = # Boris - "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a" #"<Private Key here with 0x prefix>"
acct = w3.eth.account.privateKeyToAccount(key)

# compile your smart contract with truffle first
truffleFile = json.load(open('/home/boris/Chicken_truffle_0p5/build/contracts/ChickenSubmarine.json'))
abi = truffleFile['abi']
bytecode = truffleFile['bytecode']
contract = w3.eth.contract(bytecode=bytecode, abi=abi)

#building transaction
construct_txn = contract.constructor().buildTransaction({
    'from': acct.address,
    'nonce': w3.eth.getTransactionCount(acct.address),
    'gas': 6092664,
    'gasPrice': w3.toWei('21', 'gwei')})

signed = acct.signTransaction(construct_txn)

tx_hash=w3.eth.sendRawTransaction(signed.rawTransaction)
print(tx_hash.hex())
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print("Contract Deployed At:", tx_receipt['contractAddress'])

contract = w3.eth.contract(address=tx_receipt['contractAddress'], bytecode=bytecode, abi=abi)
#return contract

#Contract Deployed At: 0xe283efD1A9D6942E0fe9d1C69957f58ADB216ae4  --- out of gas

#Contract Deployed At: 0x7844833c5f037B26Be9A8d21982756D744F1ff0d