import argparse
import json
import sys

from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract
BORIS_INFURA = "https://kovan.infura.io/v3/6a78ce7bbca14f73a8644c43eed4d2af"
OFER_INFURA = "https://kovan.infura.io/v3/b275be83f34b419bbdb7f4920e9a1d2e"
# <Private Key here with 0x prefix>
BORIS_KEY = "0xbdf5bd75f8907a1f5a34d3b1b4fddb047d4cdd71203f3301b5f230dfc1cffa7a"
OFER_KEY = "0x3B1533A9E1E80FF558BB6708F71DA1397DB10C3F590A43E19917ED55CD5D9591"

def main():
    parser = _get_args()
    infura = parser.infura
    private_key = parser.private_key
    gas = parser.gas
    gas_price = parser.gas_price

    # web3.py instance
    w3 = Web3(HTTPProvider(infura))
    assert w3.isConnected(), f"Connection problem to infura at {infura}"

    acct = w3.eth.account.privateKeyToAccount(private_key)

    # compile your smart contract with truffle first
    truffleFile = json.load(open('./contracts/compiled_contracts/ChickenSubmarine.json'))
    abi = truffleFile['abi']
    bytecode = truffleFile['bytecode']
    contract = w3.eth.contract(bytecode=bytecode, abi=abi)

    #building transaction
    construct_txn = contract.constructor().buildTransaction({
        'from': acct.address,
        'nonce': w3.eth.getTransactionCount(acct.address),
        'gas': gas,
        'gasPrice': w3.toWei(gas_price, 'gwei')})

    signed = acct.signTransaction(construct_txn)

    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    print(tx_hash.hex())
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    assert tx_receipt.status == 1, \
        f"{tx_hash.hex()} failed, receipt status should be 1, please check on etherscan.io"
    print("Contract Deployed At:", tx_receipt['contractAddress'])
    contract = w3.eth.contract(address=tx_receipt['contractAddress'], bytecode=bytecode, abi=abi)

    # write contract data to file
    contract_data = {"address": contract.address,
                     "bytecode": contract.bytecode.hex(),
                     "abi": list(contract.abi)}
    file_name = f"./contracts/deployed_contracts/{contract.address}.json"
    with open(file_name, 'w+') as json_file:
        json.dump(contract_data, json_file)

    return contract

    #Contract Deployed At: 0xe283efD1A9D6942E0fe9d1C69957f58ADB216ae4  --- out of gas

    #Contract Deployed At: 0x7844833c5f037B26Be9A8d21982756D744F1ff0d


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


if __name__ == "__main__":
    main()
