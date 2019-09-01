from _pysha3 import keccak_256
from ethereum.utils import checksum_encode
from web3 import Web3
from ethereum.abi import ContractTranslator
from ethereum.tools import tester
from ethereum import utils
from solc import compile_standard

from proveth.offchain import proveth


def rec_hex(x):
    if isinstance(x, list):
        return [rec_hex(elem) for elem in x]
    else:
        return "0x" + utils.encode_hex(x)


def rec_bin(x):
    if isinstance(x, list):
        return [rec_bin(elem) for elem in x]
    elif isinstance(x, int):
        return x
    elif isinstance(x, str):
        if x.startswith("0x"):
            return utils.decode_hex(x[2:])
        else:
            return utils.decode_hex(x)


def deploy_solidity_contract_with_args(chain, solc_config_sources, allow_paths, contract_file, contract_name, startgas, args=[], contract_creator=tester.k0):
    compiled = compile_standard({
        'language': 'Solidity',
        'sources': solc_config_sources,
        'settings': {'evmVersion': 'byzantium',
                     'outputSelection': {'*': {'*': ['abi', 'evm.bytecode']}},
                    },
    }, allow_paths=allow_paths)

    abi = compiled['contracts'][contract_file][contract_name]['abi']
    binary = compiled['contracts'][contract_file][contract_name]['evm']['bytecode']['object']
    ct = ContractTranslator(abi)
    address = chain.contract(
        utils.decode_hex(binary) + (ct.encode_constructor_arguments(args) if args else b''),
        language='evm',
        value=0,
        startgas=startgas,
        sender=contract_creator
    )
    contract = tester.ABIContract(chain, ct, address)
    return contract

def proveth_compatible_commit_block(commit_block, commit_tx):
    '''Converts a pyethereum block object (commit_block) that contains
    a single pyethereum transaction object (commit_tx) into
    the format proveth expects.
    '''
    proveth_expected_block_format_dict = dict()
    proveth_expected_block_format_dict['parentHash'] = commit_block.prevhash
    proveth_expected_block_format_dict['sha3Uncles'] = commit_block.uncles_hash
    proveth_expected_block_format_dict['miner'] = commit_block.coinbase
    proveth_expected_block_format_dict['stateRoot'] = commit_block.state_root
    proveth_expected_block_format_dict['transactionsRoot'] = commit_block.tx_list_root
    proveth_expected_block_format_dict['receiptsRoot'] = commit_block.receipts_root
    proveth_expected_block_format_dict['logsBloom'] = commit_block.bloom
    proveth_expected_block_format_dict['difficulty'] = commit_block.difficulty
    proveth_expected_block_format_dict['number'] = commit_block.number
    proveth_expected_block_format_dict['gasLimit'] = commit_block.gas_limit
    proveth_expected_block_format_dict['gasUsed'] = commit_block.gas_used
    proveth_expected_block_format_dict['timestamp'] = commit_block.timestamp
    proveth_expected_block_format_dict['extraData'] = commit_block.extra_data
    proveth_expected_block_format_dict['mixHash'] = commit_block.mixhash
    proveth_expected_block_format_dict['nonce'] = commit_block.nonce
    proveth_expected_block_format_dict['hash'] = commit_block.hash
    proveth_expected_block_format_dict['uncles'] = []

    proveth_expected_block_format_dict['transactions'] = ({
        "blockHash":          commit_block.hash,
        "blockNumber":        str(hex((commit_block['number']))),
        "from":               utils.checksum_encode(commit_tx.sender),
        "gas":                str(hex(commit_tx.startgas)),
        "gasPrice":           str(hex(commit_tx.gasprice)),
        "hash":               rec_hex(commit_tx.hash),
        "input":              rec_hex(commit_tx.data),
        "nonce":              str(hex(commit_tx.nonce)),
        "to":                 utils.checksum_encode(commit_tx.to),
        "transactionIndex":   str(hex(0)),
        "value":              str(hex(commit_tx.value)),
        "v":                  str(hex(commit_tx.v)),
        "r":                  str(hex(commit_tx.r)),
        "s":                  str(hex(commit_tx.s)),
    }, )

    return proveth_expected_block_format_dict


def keccak_256_encript_uint32(encript_input):
    """
    Encript an int using keccak_256
    :param encript_input:
    :return:
    """
    return Web3.solidityKeccak(['uint32'], [encript_input])


def generate_proof_blob(player):
    """
    Generate proof blob for this player in this game
    """
    src_address = player.user_account.address
    commit_tx_object = player.submarine_commit
    commit_block_number = player.submarine_tx_receipt.get("blockNumber")
    commit_block_object = player.w3.getBlock(commit_block_number)
    proveth_expected_block_format_dict = dict()

    # record all the data in the desired format
    proveth_expected_block_format_dict['parentHash'] = commit_block_object['prevhash']
    proveth_expected_block_format_dict['sha3Uncles'] = commit_block_object['uncles_hash']
    proveth_expected_block_format_dict['miner'] = commit_block_object['coinbase']
    proveth_expected_block_format_dict['stateRoot'] = commit_block_object['state_root']
    proveth_expected_block_format_dict['transactionsRoot'] = commit_block_object['tx_list_root']
    proveth_expected_block_format_dict['receiptsRoot'] = commit_block_object['receipts_root']
    proveth_expected_block_format_dict['logsBloom'] = commit_block_object['bloom']
    proveth_expected_block_format_dict['difficulty'] = commit_block_object['difficulty']
    proveth_expected_block_format_dict['number'] = commit_block_object['number']
    proveth_expected_block_format_dict['gasLimit'] = commit_block_object['gas_limit']
    proveth_expected_block_format_dict['gasUsed'] = commit_block_object['gas_used']
    proveth_expected_block_format_dict['timestamp'] = commit_block_object['timestamp']
    proveth_expected_block_format_dict['extraData'] = commit_block_object['extra_data']
    proveth_expected_block_format_dict['mixHash'] = commit_block_object['mixhash']
    proveth_expected_block_format_dict['nonce'] = commit_block_object['nonce']
    proveth_expected_block_format_dict['hash'] = commit_block_object.hash
    proveth_expected_block_format_dict['uncles'] = []
    proveth_expected_block_format_dict['transactions'] = \
        ({
            "blockHash": commit_block_object.hash,
            "blockNumber": str(hex((commit_block_object['number']))),
            "from": checksum_encode(src_address),
            "gas": str(hex(commit_tx_object['startgas'])),
            "gasPrice": str(hex(commit_tx_object['gasprice'])),
            "hash": rec_hex(commit_tx_object['hash']),
            "input": rec_hex(commit_tx_object['data']),
            "nonce": str(hex(commit_tx_object['nonce'])),
            "to": checksum_encode(commit_tx_object['to']),
            "transactionIndex": str(hex(0)),
            "value": str(hex(commit_tx_object['value'])),
            "v": str(hex(commit_tx_object['v'])),
            "r": str(hex(commit_tx_object['r'])),
            "s": str(hex(commit_tx_object['s']))
         },)

    return proveth.generate_proof_blob(proveth_expected_block_format_dict,
                                       player.submarine_tx_receipt.get("transactionIndex"))
