import logging
import os
import rlp
import sys
import unittest

from ethereum import config, transactions
from ethereum.tools import tester as t
from ethereum.utils import checksum_encode, normalize_address, sha3

from proveth.offchain.proveth import generate_proof_blob
from test_chicken.test_utils import rec_hex, rec_bin, deploy_solidity_contract_with_args, \
    keccak_256_encript_uint32

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'generate_commitment'))
import generate_submarine_commit

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'proveth', 'offchain'))
import proveth

root_repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

COMMIT_PERIOD_LENGTH = 20
REVEAL_PERIOD_LENGTH = 30  # hardcoded in the auction contract...
BID_AMOUNT_Alice = 1337000000000000000
BID_AMOUNT_Bob = 5555000000000000000
BID_AMOUNT_Charlie = 8675309000000000000
OURGASLIMIT = 3712394
OURGASPRICE = 10**6
BASIC_SEND_GAS_LIMIT = 21000
extraTransactionFees = 100000000000000000
ACCOUNT_STARTING_BALANCE = 1000000000000000000000000
SOLIDITY_NULL_INITIALVAL = 0
ALICE_ADDRESS = t.a1
ALICE_PRIVATE_KEY = t.k1
BOB_ADDRESS = t.a2
BOB_PRIVATE_KEY = t.k2
CHARLIE_ADDRESS = t.a3
CHARLIE_PRIVATE_KEY = t.k3
RANDO_ADDRESS_PRIVATE_KEY = t.k6
CONTRACT_OWNER_ADDRESS = t.a7
CONTRACT_OWNER_PRIVATE_KEY = t.k7
TOKEN_ID = 3

log = logging.getLogger('TestExampleChicken')
LOGFORMAT = "%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s(): %(message)s"
log.setLevel(logging.getLevelName('INFO'))
logHandler = logging.StreamHandler(stream=sys.stdout)
logHandler.setFormatter(logging.Formatter(LOGFORMAT))
log.addHandler(logHandler)


class TestExampleChicken(unittest.TestCase):
    def setUp(self):
        config.config_metropolis['BLOCK_GAS_LIMIT'] = 2**60
        self.chain = t.Chain(env=config.Env(config=config.config_metropolis))
        self.chain.mine(1)
        contract_dir = os.path.abspath(
            os.path.join(root_repo_dir, 'contracts/'))
        os.chdir(root_repo_dir)

        self.chicken_contract = deploy_solidity_contract_with_args(
            chain=self.chain,
            solc_config_sources={
                'ChickenSubmarine.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'ChickenSubmarine.sol')]
                },
                'LibSubmarineSimple.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'LibSubmarineSimple.sol')]
                },
                'openzeppelin-solidity/contracts/math/SafeMath.sol': {
                    'urls': [os.path.join(contract_dir, 'openzeppelin-solidity/contracts/math/SafeMath.sol')]
                },
                'proveth/ProvethVerifier.sol': {
                    'urls': [
                        os.path.join(contract_dir, 'proveth/ProvethVerifier.sol')]
                },
                'proveth/Solidity-RLP/contracts/RLPReader.sol': {
                    'urls': [os.path.join(contract_dir, 'proveth/Solidity-RLP/contracts/RLPReader.sol')]
                }
            },
            allow_paths=root_repo_dir,
            contract_file='ChickenSubmarine.sol',
            contract_name='ChickenSubmarine',
            startgas=10**7,
            args=[],
            contract_creator=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)

    def test_chickenWorkflow(self):
        ##
        ## STARTING STATE
        ##

        self.chain.mine(1)

        # validate initial balance
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))
        # Validate the contract is deploied
        self.assertTrue(self.chicken_contract.address)
        self.assertEqual(27, self.chicken_contract.vee())

        ##
        ## START THE GAME
        startChickenBlock = self.chain.head_state.block_number + 1
        startRevealBlock = self.chain.head_state.block_number + COMMIT_PERIOD_LENGTH
        minBet = 10
        endCommitBlockRaw = startRevealBlock - 1
        endCommitBlockCrypt = keccak_256_encript_uint32(endCommitBlockRaw)

        self.chicken_contract.initChickenGame(rec_bin(startChickenBlock),
                                              rec_bin(startRevealBlock),
                                              rec_bin(minBet),
                                              endCommitBlockCrypt,
                                              sender=CONTRACT_OWNER_PRIVATE_KEY)

        # validate chicken game initiated
        self.assertEqual(endCommitBlockCrypt, self.chicken_contract.endCommitBlockCrypt())
        self.assertEqual(minBet, self.chicken_contract.minBet())
        self.assertEqual(rec_hex(CONTRACT_OWNER_ADDRESS), self.chicken_contract.manager())
        self.assertEqual(startChickenBlock, self.chicken_contract.startBlock())
        self.assertEqual(startRevealBlock, self.chicken_contract.startRevealBlock())
        self.assertEqual(startRevealBlock+REVEAL_PERIOD_LENGTH, self.chicken_contract.endRevealBlock())
        self.assertEqual(False, self.chicken_contract.isInitiated())
        self.assertEqual(False, self.chicken_contract.winnerSelected())
        self.assertEqual(64*'0', self.chicken_contract.winningSubmarineId().hex())


        #
        # GENERATE UNLOCK TXs
        #
        commitAddressAlice, commitAlice, witnessAlice, unlock_tx_hexAlice = generate_submarine_commit.generateCommitAddress(
             normalize_address(rec_hex(ALICE_ADDRESS)),
             normalize_address(rec_hex(self.chicken_contract.address)),
             BID_AMOUNT_Alice, b'', OURGASPRICE, OURGASLIMIT)

        unlock_tx_infoAlice = rlp.decode(rec_bin(unlock_tx_hexAlice))
        unlock_tx_objectAlice = transactions.Transaction(
            int.from_bytes(unlock_tx_infoAlice[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoAlice[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoAlice[2], byteorder="big"),  # startgas
            unlock_tx_infoAlice[3],  # to addr
            int.from_bytes(unlock_tx_infoAlice[4], byteorder="big"),  # value
            unlock_tx_infoAlice[5],  # data
            int.from_bytes(unlock_tx_infoAlice[6], byteorder="big"),  # v
            int.from_bytes(unlock_tx_infoAlice[7], byteorder="big"),  # r
            int.from_bytes(unlock_tx_infoAlice[8], byteorder="big")  # s
        )
        commitAddressBob, commitBob, witnessBob, unlock_tx_hexBob = generate_submarine_commit.generateCommitAddress(
             normalize_address(rec_hex(BOB_ADDRESS)),
             normalize_address(rec_hex(self.chicken_contract.address)),
             BID_AMOUNT_Bob, b'', OURGASPRICE, OURGASLIMIT)

        unlock_tx_infoBob = rlp.decode(rec_bin(unlock_tx_hexBob))
        unlock_tx_objectBob = transactions.Transaction(
            int.from_bytes(unlock_tx_infoBob[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoBob[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoBob[2], byteorder="big"),  # startgas
            unlock_tx_infoBob[3],  # to addr
            int.from_bytes(unlock_tx_infoBob[4], byteorder="big"),  # value
            unlock_tx_infoBob[5],  # data
            int.from_bytes(unlock_tx_infoBob[6], byteorder="big"),  # v
            int.from_bytes(unlock_tx_infoBob[7], byteorder="big"),  # r
            int.from_bytes(unlock_tx_infoBob[8], byteorder="big")  # s
        )
        commitAddressCharlie, commitCharlie, witnessCharlie, unlock_tx_hexCharlie = generate_submarine_commit.generateCommitAddress(
             normalize_address(rec_hex(CHARLIE_ADDRESS)),
             normalize_address(rec_hex(self.chicken_contract.address)),
             BID_AMOUNT_Charlie, b'', OURGASPRICE, OURGASLIMIT)

        unlock_tx_infoCharlie = rlp.decode(rec_bin(unlock_tx_hexCharlie))
        unlock_tx_objectCharlie = transactions.Transaction(
            int.from_bytes(unlock_tx_infoCharlie[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoCharlie[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoCharlie[2], byteorder="big"),  # startgas
            unlock_tx_infoCharlie[3],  # to addr
            int.from_bytes(unlock_tx_infoCharlie[4], byteorder="big"),  # value
            unlock_tx_infoCharlie[5],  # data
            int.from_bytes(unlock_tx_infoCharlie[6], byteorder="big"),  # v
            int.from_bytes(unlock_tx_infoCharlie[7], byteorder="big"),  # r
            int.from_bytes(unlock_tx_infoCharlie[8], byteorder="big")  # s
        )

        #
        # GENERATE + BROADCAST COMMIT TXs
        #
        commit_tx_objectAlice = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressAlice),
            (BID_AMOUNT_Alice + extraTransactionFees),
            b'').sign(ALICE_PRIVATE_KEY)
        commit_gasAlice = int(self.chain.head_state.gas_used)

        self.chain.mine(1)
        self.chain.direct_tx(commit_tx_objectAlice)
        self.chain.mine(1)

        commit_tx_objectBob = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressBob),
            (BID_AMOUNT_Bob + extraTransactionFees),
            b'').sign(BOB_PRIVATE_KEY)
        commit_gasBob = int(self.chain.head_state.gas_used)

        self.chain.direct_tx(commit_tx_objectBob)
        self.chain.mine(1)

        commit_tx_objectCharlie = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressCharlie),
            (BID_AMOUNT_Charlie + extraTransactionFees),
            b'').sign(CHARLIE_PRIVATE_KEY)
        commit_gasCharlie = int(self.chain.head_state.gas_used)

        self.chain.direct_tx(commit_tx_objectCharlie)
        self.chain.mine(1)

        ##
        ## CHECK STATE AFTER COMMIT TX
        ##
        commit_block_numberAlice, commit_block_indexAlice = self.chain.chain.get_tx_position(
            commit_tx_objectAlice)
        self.assertEqual(BID_AMOUNT_Alice + extraTransactionFees,
                         self.chain.head_state.get_balance(commitAddressAlice))
        self.assertEqual(
            ACCOUNT_STARTING_BALANCE - (BID_AMOUNT_Alice + extraTransactionFees +
                                        BASIC_SEND_GAS_LIMIT * OURGASPRICE),
            self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))

        session_dataAlice = self.chicken_contract.getSubmarineState(rec_bin(commitAlice))
        self.assertListEqual(session_dataAlice,
                [SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL])

        revealedAndUnlocked_boolAlice = self.chicken_contract.revealedAndUnlocked(rec_bin(commitAlice))
        self.assertFalse(
            revealedAndUnlocked_boolAlice,
            "The contract should not be revealedAndUnlocked before it's even begun.")



        commit_block_numberBob, commit_block_indexBob = self.chain.chain.get_tx_position(
            commit_tx_objectBob)
        self.assertEqual(BID_AMOUNT_Bob + extraTransactionFees,
                         self.chain.head_state.get_balance(commitAddressBob))
        self.assertEqual(
            ACCOUNT_STARTING_BALANCE - (BID_AMOUNT_Bob + extraTransactionFees +
                                        BASIC_SEND_GAS_LIMIT * OURGASPRICE),
            self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))

        session_dataBob = self.chicken_contract.getSubmarineState(rec_bin(commitBob))
        self.assertListEqual(session_dataBob,
                [SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL])

        revealedAndUnlocked_boolBob = self.chicken_contract.revealedAndUnlocked(rec_bin(commitBob))
        self.assertFalse(
            revealedAndUnlocked_boolBob,
            "The contract should not be revealedAndUnlocked before it's even begun.")

        commit_block_numberCharlie, commit_block_indexCharlie = self.chain.chain.get_tx_position(
            commit_tx_objectCharlie)
        self.assertEqual(BID_AMOUNT_Charlie + extraTransactionFees,
                         self.chain.head_state.get_balance(commitAddressCharlie))
        self.assertEqual(
            ACCOUNT_STARTING_BALANCE - (BID_AMOUNT_Charlie + extraTransactionFees +
                                        BASIC_SEND_GAS_LIMIT * OURGASPRICE),
            self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))

        session_dataCharlie = self.chicken_contract.getSubmarineState(rec_bin(commitCharlie))
        self.assertListEqual(session_dataCharlie,
                [SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL, SOLIDITY_NULL_INITIALVAL])

        revealedAndUnlocked_boolCharlie = self.chicken_contract.revealedAndUnlocked(rec_bin(commitCharlie))
        self.assertFalse(
            revealedAndUnlocked_boolCharlie,
            "The contract should not be revealedAndUnlocked before it's even begun.")

        ##
        ## GENERATE AND BROADCAST REVEAL BID TXS
        ##
        self.chain.mine(COMMIT_PERIOD_LENGTH + 1)

        commit_block_objectAlice = self.chain.chain.get_block_by_number(commit_block_numberAlice)
        proveth_expected_block_format_dictAlice = dict()
        proveth_expected_block_format_dictAlice['parentHash'] = commit_block_objectAlice['prevhash']
        proveth_expected_block_format_dictAlice['sha3Uncles'] = commit_block_objectAlice['uncles_hash']
        proveth_expected_block_format_dictAlice['miner'] = commit_block_objectAlice['coinbase']
        proveth_expected_block_format_dictAlice['stateRoot'] = commit_block_objectAlice['state_root']
        proveth_expected_block_format_dictAlice['transactionsRoot'] = commit_block_objectAlice['tx_list_root']
        proveth_expected_block_format_dictAlice['receiptsRoot'] = commit_block_objectAlice['receipts_root']
        proveth_expected_block_format_dictAlice['logsBloom'] = commit_block_objectAlice['bloom']
        proveth_expected_block_format_dictAlice['difficulty'] = commit_block_objectAlice['difficulty']
        proveth_expected_block_format_dictAlice['number'] = commit_block_objectAlice['number']
        proveth_expected_block_format_dictAlice['gasLimit'] = commit_block_objectAlice['gas_limit']
        proveth_expected_block_format_dictAlice['gasUsed'] = commit_block_objectAlice['gas_used']
        proveth_expected_block_format_dictAlice['timestamp'] = commit_block_objectAlice['timestamp']
        proveth_expected_block_format_dictAlice['extraData'] = commit_block_objectAlice['extra_data']
        proveth_expected_block_format_dictAlice['mixHash'] = commit_block_objectAlice['mixhash']
        proveth_expected_block_format_dictAlice['nonce'] = commit_block_objectAlice['nonce']
        proveth_expected_block_format_dictAlice['hash'] = commit_block_objectAlice.hash
        proveth_expected_block_format_dictAlice['uncles'] = []
        proveth_expected_block_format_dictAlice['transactions'] = ({
            "blockHash":          commit_block_objectAlice.hash,
            "blockNumber":        str(hex((commit_block_objectAlice['number']))),
            "from":               checksum_encode(ALICE_ADDRESS),
            "gas":                str(hex(commit_tx_objectAlice['startgas'])),
            "gasPrice":           str(hex(commit_tx_objectAlice['gasprice'])),
            "hash":               rec_hex(commit_tx_objectAlice['hash']),
            "input":              rec_hex(commit_tx_objectAlice['data']),
            "nonce":              str(hex(commit_tx_objectAlice['nonce'])),
            "to":                 checksum_encode(commit_tx_objectAlice['to']),
            "transactionIndex":   str(hex(0)),
            "value":              str(hex(commit_tx_objectAlice['value'])),
            "v":                  str(hex(commit_tx_objectAlice['v'])),
            "r":                  str(hex(commit_tx_objectAlice['r'])),
            "s":                  str(hex(commit_tx_objectAlice['s']))
        }, )

        commit_proof_blobAlice = generate_proof_blob(
            proveth_expected_block_format_dictAlice, commit_block_indexAlice)
        _unlockExtraData = b''  # In this example we dont have any extra embedded data as part of the unlock TX


        unlock_tx_unsigned_objectAlice = transactions.UnsignedTransaction(
            int.from_bytes(unlock_tx_infoAlice[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoAlice[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoAlice[2], byteorder="big"),  # startgas
            unlock_tx_infoAlice[3],  # to addr
            int.from_bytes(unlock_tx_infoAlice[4], byteorder="big"),  # value
            unlock_tx_infoAlice[5],  # data
        )
        unlock_tx_unsigned_rlpAlice = rlp.encode(unlock_tx_unsigned_objectAlice, transactions.UnsignedTransaction)


        self.chicken_contract.reveal(
            commit_block_numberAlice,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessAlice),  # bytes32 _witness,
            unlock_tx_unsigned_rlpAlice,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobAlice,  # bytes _proofBlob
            sender=ALICE_PRIVATE_KEY)
        reveal_gasAlice = int(self.chain.head_state.gas_used)

        self.chain.mine(1)

        commit_block_objectBob = self.chain.chain.get_block_by_number(commit_block_numberBob)
        proveth_expected_block_format_dictBob = dict()
        proveth_expected_block_format_dictBob['parentHash'] = commit_block_objectBob['prevhash']
        proveth_expected_block_format_dictBob['sha3Uncles'] = commit_block_objectBob['uncles_hash']
        proveth_expected_block_format_dictBob['miner'] = commit_block_objectBob['coinbase']
        proveth_expected_block_format_dictBob['stateRoot'] = commit_block_objectBob['state_root']
        proveth_expected_block_format_dictBob['transactionsRoot'] = commit_block_objectBob['tx_list_root']
        proveth_expected_block_format_dictBob['receiptsRoot'] = commit_block_objectBob['receipts_root']
        proveth_expected_block_format_dictBob['logsBloom'] = commit_block_objectBob['bloom']
        proveth_expected_block_format_dictBob['difficulty'] = commit_block_objectBob['difficulty']
        proveth_expected_block_format_dictBob['number'] = commit_block_objectBob['number']
        proveth_expected_block_format_dictBob['gasLimit'] = commit_block_objectBob['gas_limit']
        proveth_expected_block_format_dictBob['gasUsed'] = commit_block_objectBob['gas_used']
        proveth_expected_block_format_dictBob['timestamp'] = commit_block_objectBob['timestamp']
        proveth_expected_block_format_dictBob['extraData'] = commit_block_objectBob['extra_data']
        proveth_expected_block_format_dictBob['mixHash'] = commit_block_objectBob['mixhash']
        proveth_expected_block_format_dictBob['nonce'] = commit_block_objectBob['nonce']
        proveth_expected_block_format_dictBob['hash'] = commit_block_objectBob.hash
        proveth_expected_block_format_dictBob['uncles'] = []
        proveth_expected_block_format_dictBob['transactions'] = ({
            "blockHash":          commit_block_objectBob.hash,
            "blockNumber":        str(hex((commit_block_objectBob['number']))),
            "from":               checksum_encode(BOB_ADDRESS),
            "gas":                str(hex(commit_tx_objectBob['startgas'])),
            "gasPrice":           str(hex(commit_tx_objectBob['gasprice'])),
            "hash":               rec_hex(commit_tx_objectBob['hash']),
            "input":              rec_hex(commit_tx_objectBob['data']),
            "nonce":              str(hex(commit_tx_objectBob['nonce'])),
            "to":                 checksum_encode(commit_tx_objectBob['to']),
            "transactionIndex":   str(hex(0)),
            "value":              str(hex(commit_tx_objectBob['value'])),
            "v":                  str(hex(commit_tx_objectBob['v'])),
            "r":                  str(hex(commit_tx_objectBob['r'])),
            "s":                  str(hex(commit_tx_objectBob['s']))
        }, )

        commit_proof_blobBob = generate_proof_blob(
            proveth_expected_block_format_dictBob, commit_block_indexBob)
        _unlockExtraData = b''  # In this example we dont have any extra embedded data as part of the unlock TX


        unlock_tx_unsigned_objectBob = transactions.UnsignedTransaction(
            int.from_bytes(unlock_tx_infoBob[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoBob[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoBob[2], byteorder="big"),  # startgas
            unlock_tx_infoBob[3],  # to addr
            int.from_bytes(unlock_tx_infoBob[4], byteorder="big"),  # value
            unlock_tx_infoBob[5],  # data
        )
        unlock_tx_unsigned_rlpBob = rlp.encode(unlock_tx_unsigned_objectBob, transactions.UnsignedTransaction)


        self.chicken_contract.reveal(
            commit_block_numberBob,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessBob),  # bytes32 _witness,
            unlock_tx_unsigned_rlpBob,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobBob,  # bytes _proofBlob
            sender=BOB_PRIVATE_KEY)
        reveal_gasBob = int(self.chain.head_state.gas_used)

        self.chain.mine(1)

        commit_block_objectCharlie = self.chain.chain.get_block_by_number(commit_block_numberCharlie)
        proveth_expected_block_format_dictCharlie = dict()
        proveth_expected_block_format_dictCharlie['parentHash'] = commit_block_objectCharlie['prevhash']
        proveth_expected_block_format_dictCharlie['sha3Uncles'] = commit_block_objectCharlie['uncles_hash']
        proveth_expected_block_format_dictCharlie['miner'] = commit_block_objectCharlie['coinbase']
        proveth_expected_block_format_dictCharlie['stateRoot'] = commit_block_objectCharlie['state_root']
        proveth_expected_block_format_dictCharlie['transactionsRoot'] = commit_block_objectCharlie['tx_list_root']
        proveth_expected_block_format_dictCharlie['receiptsRoot'] = commit_block_objectCharlie['receipts_root']
        proveth_expected_block_format_dictCharlie['logsBloom'] = commit_block_objectCharlie['bloom']
        proveth_expected_block_format_dictCharlie['difficulty'] = commit_block_objectCharlie['difficulty']
        proveth_expected_block_format_dictCharlie['number'] = commit_block_objectCharlie['number']
        proveth_expected_block_format_dictCharlie['gasLimit'] = commit_block_objectCharlie['gas_limit']
        proveth_expected_block_format_dictCharlie['gasUsed'] = commit_block_objectCharlie['gas_used']
        proveth_expected_block_format_dictCharlie['timestamp'] = commit_block_objectCharlie['timestamp']
        proveth_expected_block_format_dictCharlie['extraData'] = commit_block_objectCharlie['extra_data']
        proveth_expected_block_format_dictCharlie['mixHash'] = commit_block_objectCharlie['mixhash']
        proveth_expected_block_format_dictCharlie['nonce'] = commit_block_objectCharlie['nonce']
        proveth_expected_block_format_dictCharlie['hash'] = commit_block_objectCharlie.hash
        proveth_expected_block_format_dictCharlie['uncles'] = []
        proveth_expected_block_format_dictCharlie['transactions'] = ({
            "blockHash":          commit_block_objectCharlie.hash,
            "blockNumber":        str(hex((commit_block_objectCharlie['number']))),
            "from":               checksum_encode(CHARLIE_ADDRESS),
            "gas":                str(hex(commit_tx_objectCharlie['startgas'])),
            "gasPrice":           str(hex(commit_tx_objectCharlie['gasprice'])),
            "hash":               rec_hex(commit_tx_objectCharlie['hash']),
            "input":              rec_hex(commit_tx_objectCharlie['data']),
            "nonce":              str(hex(commit_tx_objectCharlie['nonce'])),
            "to":                 checksum_encode(commit_tx_objectCharlie['to']),
            "transactionIndex":   str(hex(0)),
            "value":              str(hex(commit_tx_objectCharlie['value'])),
            "v":                  str(hex(commit_tx_objectCharlie['v'])),
            "r":                  str(hex(commit_tx_objectCharlie['r'])),
            "s":                  str(hex(commit_tx_objectCharlie['s']))
        }, )

        commit_proof_blobCharlie = generate_proof_blob(
            proveth_expected_block_format_dictCharlie, commit_block_indexCharlie)
        _unlockExtraData = b''  # In this example we dont have any extra embedded data as part of the unlock TX


        unlock_tx_unsigned_objectCharlie = transactions.UnsignedTransaction(
            int.from_bytes(unlock_tx_infoCharlie[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoCharlie[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoCharlie[2], byteorder="big"),  # startgas
            unlock_tx_infoCharlie[3],  # to addr
            int.from_bytes(unlock_tx_infoCharlie[4], byteorder="big"),  # value
            unlock_tx_infoCharlie[5],  # data
        )
        unlock_tx_unsigned_rlpCharlie = rlp.encode(unlock_tx_unsigned_objectCharlie, transactions.UnsignedTransaction)


        self.chicken_contract.reveal(
            commit_block_numberCharlie,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessCharlie),  # bytes32 _witness,
            unlock_tx_unsigned_rlpCharlie,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobCharlie,  # bytes _proofBlob
            sender=CHARLIE_PRIVATE_KEY)
        reveal_gasCharlie = int(self.chain.head_state.gas_used)

        self.chain.mine(1)

        ##
        ## CHECK THE STATE AFTER REVEAL
        ##
        bidRecordAlice = self.chicken_contract.players(rec_bin(commitAlice))
        self.assertEqual(rec_hex(ALICE_ADDRESS), bidRecordAlice)
        session_dataAlice = self.chicken_contract.getSubmarineState(rec_bin(commitAlice))
        self.assertListEqual(session_dataAlice, [BID_AMOUNT_Alice, SOLIDITY_NULL_INITIALVAL, commit_block_numberAlice, commit_block_indexAlice])
        revealedAndUnlocked_boolAlice = self.chicken_contract.revealedAndUnlocked(rec_bin(commitAlice))
        self.assertFalse(revealedAndUnlocked_boolAlice)

        bidRecordBob = self.chicken_contract.players(rec_bin(commitBob))
        self.assertEqual(rec_hex(BOB_ADDRESS), bidRecordBob)
        session_dataBob = self.chicken_contract.getSubmarineState(rec_bin(commitBob))
        self.assertListEqual(session_dataBob, [BID_AMOUNT_Bob, SOLIDITY_NULL_INITIALVAL, commit_block_numberBob, commit_block_indexBob])
        revealedAndUnlocked_boolBob = self.chicken_contract.revealedAndUnlocked(rec_bin(commitBob))
        self.assertFalse(revealedAndUnlocked_boolBob)

        bidRecordCharlie = self.chicken_contract.players(rec_bin(commitCharlie))
        self.assertEqual(rec_hex(CHARLIE_ADDRESS), bidRecordCharlie)
        session_dataCharlie = self.chicken_contract.getSubmarineState(rec_bin(commitCharlie))
        self.assertListEqual(session_dataCharlie, [BID_AMOUNT_Charlie, SOLIDITY_NULL_INITIALVAL, commit_block_numberCharlie, commit_block_indexCharlie])
        revealedAndUnlocked_boolCharlie = self.chicken_contract.revealedAndUnlocked(rec_bin(commitCharlie))
        self.assertFalse(revealedAndUnlocked_boolCharlie)

        ##
        ## BROADCAST UNLOCK
        ##
        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectAlice)
        unlock_gasAlice = int(self.chain.head_state.gas_used)
        self.chain.mine(1)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectBob)
        unlock_gasBob = int(self.chain.head_state.gas_used)
        self.chain.mine(1)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectCharlie)
        unlock_gasCharlie = int(self.chain.head_state.gas_used)
        self.chain.mine(1)

        ##
        ## CHECK STATE AFTER UNLOCK
        ##

        # # stuff to help with debugging
        # # unlock_block_numberAlice, unlock_block_indexAlice = self.chain.chain.get_tx_position(
        # #         unlock_tx_objectAlice)
        # # unlock_block_objectAlice = self.chain.chain.get_block_by_number(unlock_block_numberAlice)
        # # print(unlock_block_objectAlice.as_dict())

        self.assertEqual(
            self.chain.head_state.get_balance(commitAddressAlice),
            (extraTransactionFees - unlock_gasAlice*OURGASPRICE),
            "Commit address should send along the money and have almost 0 money left."
        )

        self.assertEqual(
            self.chain.head_state.get_balance(commitAddressBob),
            (extraTransactionFees - unlock_gasBob*OURGASPRICE),
            "Commit address should send along the money and have almost 0 money left."
        )

        self.assertEqual(
            self.chain.head_state.get_balance(commitAddressCharlie),
            (extraTransactionFees - unlock_gasCharlie*OURGASPRICE),
            "Commit address should send along the money and have almost 0 money left."
        )

        self.assertEqual(
            self.chain.head_state.get_balance(self.chicken_contract.address),
            (BID_AMOUNT_Alice + BID_AMOUNT_Bob + BID_AMOUNT_Charlie),
            "Contract address should have the sum of the bids balance."
        )


        session_dataAlice = self.chicken_contract.getSubmarineState(rec_bin(commitAlice))
        self.assertListEqual(session_dataAlice, [BID_AMOUNT_Alice, BID_AMOUNT_Alice, commit_block_numberAlice, commit_block_indexAlice])
        revealedAndUnlocked_boolAlice = self.chicken_contract.revealedAndUnlocked(rec_bin(commitAlice))
        self.assertTrue(revealedAndUnlocked_boolAlice)

        session_dataBob = self.chicken_contract.getSubmarineState(rec_bin(commitBob))
        self.assertListEqual(session_dataBob, [BID_AMOUNT_Bob, BID_AMOUNT_Bob, commit_block_numberBob, commit_block_indexBob])
        revealedAndUnlocked_boolBob = self.chicken_contract.revealedAndUnlocked(rec_bin(commitBob))
        self.assertTrue(revealedAndUnlocked_boolBob)

        session_dataCharlie = self.chicken_contract.getSubmarineState(rec_bin(commitCharlie))
        self.assertListEqual(session_dataCharlie, [BID_AMOUNT_Charlie, BID_AMOUNT_Charlie, commit_block_numberCharlie, commit_block_indexCharlie])
        revealedAndUnlocked_boolCharlie = self.chicken_contract.revealedAndUnlocked(rec_bin(commitCharlie))
        self.assertTrue(revealedAndUnlocked_boolCharlie)

        ###############
        # Select winner
        ###############
        self.chain.mine(REVEAL_PERIOD_LENGTH)

        self.chicken_contract._helper_kaka(endCommitBlockRaw)
        self.chain.mine(1)

        kakaBlockNum = self.chicken_contract.kakaBlockNum()

        self.chicken_contract.selectWinner(rec_bin(endCommitBlockRaw),
                                           sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)
        self.assertTrue(self.chicken_contract.winnerSelected())
        self.assertEqual(commitCharlie, self.chicken_contract.winningSubmarineId().hex())

        #####################
        # END AUCTION
        #####################
        self.chicken_contract.finalize(rec_bin(commitAlice), sender=ALICE_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitBob), sender=BOB_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitCharlie), sender=CHARLIE_PRIVATE_KEY)

        # ##
        # ## CHECK STATE NOW THAT AUCTION IS OVER

        self.assertEqual(commitCharlie, self.chicken_contract.winningSubmarineId().hex())

    def test_highest_bidder(self):
        """
        Test game with all players place bet at the same block
        1. Create game and player
        2. Place al bets at the same block
        3. reveal and unlock all the submarines
        4. Select winner and finalize the game
        5. Validate the winner is the highest bidder
        """

        self.chain.mine(1)
        # validate initial balance
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))
        # Validate the contract is deploied
        self.assertTrue(self.chicken_contract.address)
        self.assertEqual(27, self.chicken_contract.vee())

        #################
        ## START THE GAME
        #################
        startChickenBlock = self.chain.head_state.block_number + 1
        startRevealBlock = self.chain.head_state.block_number + COMMIT_PERIOD_LENGTH
        minBet = 10
        endCommitBlockRaw = startRevealBlock - 1
        endCommitBlockCrypt = keccak_256_encript_uint32(endCommitBlockRaw)

        log.info(f"Init game with start block {startChickenBlock} and end block {endCommitBlockRaw}")
        self.chicken_contract.initChickenGame(rec_bin(startChickenBlock),
                                              rec_bin(startRevealBlock),
                                              rec_bin(minBet),
                                              endCommitBlockCrypt,
                                              sender=CONTRACT_OWNER_PRIVATE_KEY)

        ##################
        # GENERATE UNLOCK TXs
        ##################
        log.info(f"Generate commit address and unlock transaction for Alice")

        commitAddressAlice, commitAlice, witnessAlice, unlock_tx_hexAlice = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(ALICE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Alice, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoAlice = rlp.decode(rec_bin(unlock_tx_hexAlice))
        unlock_tx_objectAlice = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoAlice)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressBob, commitBob, witnessBob, unlock_tx_hexBob = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(BOB_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Bob, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoBob = rlp.decode(rec_bin(unlock_tx_hexBob))
        unlock_tx_objectBob = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoBob)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressCharlie, commitCharlie, witnessCharlie, unlock_tx_hexCharlie = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(CHARLIE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Charlie, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoCharlie = rlp.decode(rec_bin(unlock_tx_hexCharlie))
        unlock_tx_objectCharlie = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoCharlie)

        ###################################
        # GENERATE + BROADCAST COMMIT TXs
        ###################################

        log.info(f"Send all submarines at the same block")

        commit_tx_objectAlice = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressAlice),
            (BID_AMOUNT_Alice + extraTransactionFees),
            b'').sign(ALICE_PRIVATE_KEY)

        commit_tx_objectBob = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressBob),
            (BID_AMOUNT_Bob + extraTransactionFees),
            b'').sign(BOB_PRIVATE_KEY)

        commit_tx_objectCharlie = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressCharlie),
            (BID_AMOUNT_Charlie + extraTransactionFees),
            b'').sign(CHARLIE_PRIVATE_KEY)

        self.chain.mine(1)
        self.chain.direct_tx(commit_tx_objectAlice)
        self.chain.direct_tx(commit_tx_objectBob)
        self.chain.direct_tx(commit_tx_objectCharlie)
        self.chain.mine(1)


        #####################################################
        ## GENERATE AND BROADCAST REVEAL BID TXS
        #####################################################
        log.info(f"Fast forward to reveal period")
        self.chain.mine(COMMIT_PERIOD_LENGTH + 1)

        ## GENERATE Prof blobs
        log.info(f"Generate all proof blobs")
        commit_block_numberAlice, commit_block_indexAlice = self.chain.chain.get_tx_position(commit_tx_objectAlice)
        commit_block_numberBob, commit_block_indexBob = self.chain.chain.get_tx_position(commit_tx_objectBob)
        commit_block_numberCharlie, commit_block_indexCharlie = self.chain.chain.get_tx_position(commit_tx_objectCharlie)

        commit_proof_blobAlice = self._generate_proof_block_wrapper(
            commit_block_numberAlice, commit_block_indexAlice, commit_tx_objectAlice, ALICE_ADDRESS)
        commit_proof_blobBob = self._generate_proof_block_wrapper(
            commit_block_numberBob, commit_block_indexBob, commit_tx_objectBob, BOB_ADDRESS)
        commit_proof_blobCharlie = self._generate_proof_block_wrapper(
            commit_block_numberCharlie, commit_block_indexCharlie, commit_tx_objectCharlie, CHARLIE_ADDRESS)

        log.info(f"Generate unsigned tx for reveal")
        unlock_tx_unsigned_rlpAlice = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoAlice)
        unlock_tx_unsigned_rlpBob = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoBob)
        unlock_tx_unsigned_rlpCharlie = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoCharlie)
        _unlockExtraData = b''

        log.info(f"Send Alice reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberAlice,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessAlice),  # bytes32 _witness,
            unlock_tx_unsigned_rlpAlice,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobAlice,  # bytes _proofBlob
            sender=ALICE_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Bob reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberBob,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessBob),  # bytes32 _witness,
            unlock_tx_unsigned_rlpBob,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobBob,  # bytes _proofBlob
            sender=BOB_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Charlie reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberCharlie,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessCharlie),  # bytes32 _witness,
            unlock_tx_unsigned_rlpCharlie,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobCharlie,  # bytes _proofBlob
            sender=CHARLIE_PRIVATE_KEY)
        self.chain.mine(1)

        ####################################
        ## BROADCAST UNLOCK
        ####################################

        log.info(f"Broadcast unlock for all players")
        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectAlice)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectBob)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectCharlie)
        self.chain.mine(1)

        #################################################
        # Select winner
        #################################################
        log.info(f"Fast forward to the end of reveal period and select winner")
        self.chain.mine(REVEAL_PERIOD_LENGTH)
        self.chicken_contract.selectWinner(rec_bin(endCommitBlockRaw),sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)
        self.assertTrue(self.chicken_contract.winnerSelected())

        log.info(f"Validate Charlie is the winner")
        self.assertEqual(commitCharlie, self.chicken_contract.winningSubmarineId().hex())

        #######################################################
        # END GAME
        #######################################################
        log.info(f"finalize game by all players")
        self.chicken_contract.finalize(rec_bin(commitAlice), sender=ALICE_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitBob), sender=BOB_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitCharlie), sender=CHARLIE_PRIVATE_KEY)

    def test_first_revealer(self):
        """
        Test game with all players place bet at the same block
        1. Create game and player
        2. Place al bets at the same block with the same bet amount
        3. reveal and unlock all the submarines
        4. Select winner and finalize the game
        5. Validate the winner is the first revealer
        """
        SAME_BID_AMOUNT = BID_AMOUNT_Alice
        self.chain.mine(1)
        # validate initial balance
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))
        # Validate the contract is deploied
        self.assertTrue(self.chicken_contract.address)
        self.assertEqual(27, self.chicken_contract.vee())

        #################
        ## START THE GAME
        #################
        startChickenBlock = self.chain.head_state.block_number + 1
        startRevealBlock = self.chain.head_state.block_number + COMMIT_PERIOD_LENGTH
        minBet = 10
        endCommitBlockRaw = startRevealBlock - 1
        endCommitBlockCrypt = keccak_256_encript_uint32(endCommitBlockRaw)

        log.info(f"Init game with start block {startChickenBlock} and end block {endCommitBlockRaw}")
        self.chicken_contract.initChickenGame(rec_bin(startChickenBlock),
                                              rec_bin(startRevealBlock),
                                              rec_bin(minBet),
                                              endCommitBlockCrypt,
                                              sender=CONTRACT_OWNER_PRIVATE_KEY)

        ##################
        # GENERATE UNLOCK TXs
        ##################
        log.info(f"Generate commit address and unlock transaction for Alice")

        commitAddressAlice, commitAlice, witnessAlice, unlock_tx_hexAlice = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(ALICE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoAlice = rlp.decode(rec_bin(unlock_tx_hexAlice))
        unlock_tx_objectAlice = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoAlice)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressBob, commitBob, witnessBob, unlock_tx_hexBob = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(BOB_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoBob = rlp.decode(rec_bin(unlock_tx_hexBob))
        unlock_tx_objectBob = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoBob)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressCharlie, commitCharlie, witnessCharlie, unlock_tx_hexCharlie = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(CHARLIE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoCharlie = rlp.decode(rec_bin(unlock_tx_hexCharlie))
        unlock_tx_objectCharlie = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoCharlie)

        ###################################
        # GENERATE + BROADCAST COMMIT TXs
        ###################################

        log.info(f"Send all submarines at the same block with the same bid amount = {SAME_BID_AMOUNT}")

        commit_tx_objectAlice = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressAlice),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(ALICE_PRIVATE_KEY)

        commit_tx_objectBob = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressBob),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(BOB_PRIVATE_KEY)

        commit_tx_objectCharlie = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressCharlie),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(CHARLIE_PRIVATE_KEY)

        self.chain.mine(1)
        self.chain.direct_tx(commit_tx_objectAlice)
        self.chain.direct_tx(commit_tx_objectBob)
        self.chain.direct_tx(commit_tx_objectCharlie)
        self.chain.mine(1)


        #####################################################
        ## GENERATE AND BROADCAST REVEAL BID TXS
        #####################################################
        log.info(f"Fast forward to reveal period")
        self.chain.mine(COMMIT_PERIOD_LENGTH + 1)

        ## GENERATE Prof blobs
        log.info(f"Generate all proof blobs")
        commit_block_numberAlice, commit_block_indexAlice = self.chain.chain.get_tx_position(commit_tx_objectAlice)
        commit_block_numberBob, commit_block_indexBob = self.chain.chain.get_tx_position(commit_tx_objectBob)
        commit_block_numberCharlie, commit_block_indexCharlie = self.chain.chain.get_tx_position(commit_tx_objectCharlie)

        commit_proof_blobAlice = self._generate_proof_block_wrapper(
            commit_block_numberAlice, commit_block_indexAlice, commit_tx_objectAlice, ALICE_ADDRESS)
        commit_proof_blobBob = self._generate_proof_block_wrapper(
            commit_block_numberBob, commit_block_indexBob, commit_tx_objectBob, BOB_ADDRESS)
        commit_proof_blobCharlie = self._generate_proof_block_wrapper(
            commit_block_numberCharlie, commit_block_indexCharlie, commit_tx_objectCharlie, CHARLIE_ADDRESS)

        log.info(f"Generate unsigned tx for reveal")
        unlock_tx_unsigned_rlpAlice = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoAlice)
        unlock_tx_unsigned_rlpBob = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoBob)
        unlock_tx_unsigned_rlpCharlie = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoCharlie)
        _unlockExtraData = b''

        log.info(f"Send Alice reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberAlice,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessAlice),  # bytes32 _witness,
            unlock_tx_unsigned_rlpAlice,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobAlice,  # bytes _proofBlob
            sender=ALICE_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Bob reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberBob,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessBob),  # bytes32 _witness,
            unlock_tx_unsigned_rlpBob,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobBob,  # bytes _proofBlob
            sender=BOB_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Charlie reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberCharlie,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessCharlie),  # bytes32 _witness,
            unlock_tx_unsigned_rlpCharlie,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobCharlie,  # bytes _proofBlob
            sender=CHARLIE_PRIVATE_KEY)
        self.chain.mine(1)

        ####################################
        ## BROADCAST UNLOCK
        ####################################

        log.info(f"Broadcast unlock for all players")
        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectAlice)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectBob)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectCharlie)
        self.chain.mine(1)

        #################################################
        # Select winner
        #################################################
        log.info(f"Fast forward to the end of reveal period and select winner")
        self.chain.mine(REVEAL_PERIOD_LENGTH)
        self.chicken_contract.selectWinner(rec_bin(endCommitBlockRaw), sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)
        self.assertTrue(self.chicken_contract.winnerSelected())

        log.info(f"Validate ALICE is the winner")
        self.assertEqual(commitAlice, self.chicken_contract.winningSubmarineId().hex())

        #######################################################
        # END GAME
        #######################################################
        log.info(f"finalize game by all players")
        self.chicken_contract.finalize(rec_bin(commitAlice), sender=ALICE_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitBob), sender=BOB_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitCharlie), sender=CHARLIE_PRIVATE_KEY)

    def test_one_player_off(self):
        """
        Test game one player place bet after commit period and before reveal period
        1. Create game and player
        2. Place two bets in the commit period and another one after
        3. reveal and unlock all the submarines
        4. Select winner and finalize the game
        5. Validate the bob is the winner
        """

        self.chain.mine(1)
        # validate initial balance
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))
        # Validate the contract is deploied
        self.assertTrue(self.chicken_contract.address)
        self.assertEqual(27, self.chicken_contract.vee())

        #################
        ## START THE GAME
        #################
        startChickenBlock = self.chain.head_state.block_number + 1
        startRevealBlock = self.chain.head_state.block_number + COMMIT_PERIOD_LENGTH
        minBet = 10
        endCommitBlockRaw = startRevealBlock - 10
        endCommitBlockCrypt = keccak_256_encript_uint32(endCommitBlockRaw)

        log.info(f"Init game with start block {startChickenBlock} and end commit block {endCommitBlockRaw}")
        self.chicken_contract.initChickenGame(rec_bin(startChickenBlock),
                                              rec_bin(startRevealBlock),
                                              rec_bin(minBet),
                                              endCommitBlockCrypt,
                                              sender=CONTRACT_OWNER_PRIVATE_KEY)

        ##################
        # GENERATE UNLOCK TXs
        ##################
        log.info(f"Generate commit address and unlock transaction for Alice")

        commitAddressAlice, commitAlice, witnessAlice, unlock_tx_hexAlice = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(ALICE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Alice, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoAlice = rlp.decode(rec_bin(unlock_tx_hexAlice))
        unlock_tx_objectAlice = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoAlice)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressBob, commitBob, witnessBob, unlock_tx_hexBob = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(BOB_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Bob, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoBob = rlp.decode(rec_bin(unlock_tx_hexBob))
        unlock_tx_objectBob = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoBob)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressCharlie, commitCharlie, witnessCharlie, unlock_tx_hexCharlie = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(CHARLIE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            BID_AMOUNT_Charlie, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoCharlie = rlp.decode(rec_bin(unlock_tx_hexCharlie))
        unlock_tx_objectCharlie = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoCharlie)

        ###################################
        # GENERATE + BROADCAST COMMIT TXs
        ###################################


        commit_tx_objectAlice = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressAlice),
            (BID_AMOUNT_Alice + extraTransactionFees),
            b'').sign(ALICE_PRIVATE_KEY)

        commit_tx_objectBob = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressBob),
            (BID_AMOUNT_Bob + extraTransactionFees),
            b'').sign(BOB_PRIVATE_KEY)

        commit_tx_objectCharlie = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressCharlie),
            (BID_AMOUNT_Charlie + extraTransactionFees),
            b'').sign(CHARLIE_PRIVATE_KEY)

        self.chain.mine(1)
        log.info(f"Send alice submarine at block {self.chain.head_state.block_number}")
        self.chain.direct_tx(commit_tx_objectAlice)
        self.chain.mine(1)
        log.info(f"Send Bob submarine at block {self.chain.head_state.block_number}")
        self.chain.direct_tx(commit_tx_objectBob)

        log.info(f"Fast forward to end of commit period")
        self.chain.mine(COMMIT_PERIOD_LENGTH - 5)
        log.info(f"Send Charlie submarine at block {self.chain.head_state.block_number}")
        self.chain.direct_tx(commit_tx_objectCharlie)
        self.chain.mine(1)


        #####################################################
        ## GENERATE AND BROADCAST REVEAL BID TXS
        #####################################################
        log.info(f"Fast forward to reveal period")
        self.chain.mine(startRevealBlock - self.chain.head_state.block_number + 1)

        ## GENERATE Prof blobs
        log.info(f"Generate all proof blobs")
        commit_block_numberAlice, commit_block_indexAlice = self.chain.chain.get_tx_position(commit_tx_objectAlice)
        commit_block_numberBob, commit_block_indexBob = self.chain.chain.get_tx_position(commit_tx_objectBob)
        commit_block_numberCharlie, commit_block_indexCharlie = self.chain.chain.get_tx_position(commit_tx_objectCharlie)

        commit_proof_blobAlice = self._generate_proof_block_wrapper(
            commit_block_numberAlice, commit_block_indexAlice, commit_tx_objectAlice, ALICE_ADDRESS)
        commit_proof_blobBob = self._generate_proof_block_wrapper(
            commit_block_numberBob, commit_block_indexBob, commit_tx_objectBob, BOB_ADDRESS)
        commit_proof_blobCharlie = self._generate_proof_block_wrapper(
            commit_block_numberCharlie, commit_block_indexCharlie, commit_tx_objectCharlie, CHARLIE_ADDRESS)

        log.info(f"Generate unsigned tx for reveal")
        unlock_tx_unsigned_rlpAlice = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoAlice)
        unlock_tx_unsigned_rlpBob = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoBob)
        unlock_tx_unsigned_rlpCharlie = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoCharlie)
        _unlockExtraData = b''

        log.info(f"Send Alice reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberAlice,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessAlice),  # bytes32 _witness,
            unlock_tx_unsigned_rlpAlice,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobAlice,  # bytes _proofBlob
            sender=ALICE_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Bob reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberBob,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessBob),  # bytes32 _witness,
            unlock_tx_unsigned_rlpBob,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobBob,  # bytes _proofBlob
            sender=BOB_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Charlie reveal tx at block {self.chain.block.header.number}")
        self.chicken_contract.reveal(
            commit_block_numberCharlie,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessCharlie),  # bytes32 _witness,
            unlock_tx_unsigned_rlpCharlie,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobCharlie,  # bytes _proofBlob
            sender=CHARLIE_PRIVATE_KEY)
        self.chain.mine(1)

        ####################################
        ## BROADCAST UNLOCK
        ####################################

        log.info(f"Broadcast unlock for all players")
        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectAlice)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectBob)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectCharlie)
        self.chain.mine(1)

        #################################################
        # Select winner
        #################################################
        log.info(f"Fast forward to the end of reveal period and select winner")
        self.chain.mine(REVEAL_PERIOD_LENGTH)
        self.chicken_contract.selectWinner(rec_bin(endCommitBlockRaw),sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)
        self.assertTrue(self.chicken_contract.winnerSelected())

        log.info(f"Validate Bob is the winner")
        self.assertEqual(commitBob, self.chicken_contract.winningSubmarineId().hex())

        #######################################################
        # END GAME
        #######################################################
        log.info(f"finalize game by all players")
        self.chicken_contract.finalize(rec_bin(commitAlice), sender=ALICE_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitBob), sender=BOB_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitCharlie), sender=CHARLIE_PRIVATE_KEY)

    def test_no_winner_late_commit(self):
        """
        Test game with all players placing a bet after the end commit block and before start reveal period
        1. Create game and player
        2. Wait for commit period to end
        2. Place all bets before reveal period starts
        3. reveal and unlock all the submarines
        4. Select winner and finalize the game
        5. Validate no winner was selected
        """
        SAME_BID_AMOUNT = BID_AMOUNT_Alice
        self.chain.mine(1)
        # validate initial balance
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(BOB_ADDRESS)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE, self.chain.head_state.get_balance(rec_hex(CHARLIE_ADDRESS)))
        # Validate the contract is deploied
        self.assertTrue(self.chicken_contract.address)
        self.assertEqual(27, self.chicken_contract.vee())

        #################
        ## START THE GAME
        #################
        startChickenBlock = self.chain.head_state.block_number + 1
        startRevealBlock = self.chain.head_state.block_number + COMMIT_PERIOD_LENGTH
        minBet = 10
        endCommitBlockRaw = startRevealBlock - 10
        endCommitBlockCrypt = keccak_256_encript_uint32(endCommitBlockRaw)

        log.info(f"Init game with start block {startChickenBlock} and end commit block {endCommitBlockRaw}")
        self.chicken_contract.initChickenGame(rec_bin(startChickenBlock),
                                              rec_bin(startRevealBlock),
                                              rec_bin(minBet),
                                              endCommitBlockCrypt,
                                              sender=CONTRACT_OWNER_PRIVATE_KEY)

        ##################
        # GENERATE UNLOCK TXs
        ##################
        log.info(f"Fast forward to block {startChickenBlock + COMMIT_PERIOD_LENGTH - 3} - the end of commit period")
        self.chain.mine(COMMIT_PERIOD_LENGTH - 5)

        log.info(f"Generate commit address and unlock transaction for Alice")

        commitAddressAlice, commitAlice, witnessAlice, unlock_tx_hexAlice = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(ALICE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoAlice = rlp.decode(rec_bin(unlock_tx_hexAlice))
        unlock_tx_objectAlice = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoAlice)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressBob, commitBob, witnessBob, unlock_tx_hexBob = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(BOB_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoBob = rlp.decode(rec_bin(unlock_tx_hexBob))
        unlock_tx_objectBob = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoBob)

        log.info(f"Generate commit address and unlock transaction for Bob")
        commitAddressCharlie, commitCharlie, witnessCharlie, unlock_tx_hexCharlie = generate_submarine_commit.generateCommitAddress(
            normalize_address(rec_hex(CHARLIE_ADDRESS)),
            normalize_address(rec_hex(self.chicken_contract.address)),
            SAME_BID_AMOUNT, b'', OURGASPRICE, OURGASLIMIT)
        unlock_tx_infoCharlie = rlp.decode(rec_bin(unlock_tx_hexCharlie))
        unlock_tx_objectCharlie = self._create_unlock_transaction(unlock_tx_infoAlice=unlock_tx_infoCharlie)

        ###################################
        # GENERATE + BROADCAST COMMIT TXs
        ###################################

        log.info(f"Send all submarines at the same block ({self.chain.head_state.block_number}) "
                 f"with the same bid amount = {SAME_BID_AMOUNT}")

        commit_tx_objectAlice = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressAlice),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(ALICE_PRIVATE_KEY)

        commit_tx_objectBob = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressBob),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(BOB_PRIVATE_KEY)

        commit_tx_objectCharlie = transactions.Transaction(
            0, OURGASPRICE, BASIC_SEND_GAS_LIMIT, rec_bin(commitAddressCharlie),
            (SAME_BID_AMOUNT + extraTransactionFees),
            b'').sign(CHARLIE_PRIVATE_KEY)

        self.chain.mine(1)
        self.chain.direct_tx(commit_tx_objectAlice)
        self.chain.direct_tx(commit_tx_objectBob)
        self.chain.direct_tx(commit_tx_objectCharlie)
        self.chain.mine(1)


        #####################################################
        ## GENERATE AND BROADCAST REVEAL BID TXS
        #####################################################
        log.info(f"Fast forward to reveal period")
        self.chain.mine(startRevealBlock - self.chain.head_state.block_number + 2)

        ## GENERATE Prof blobs
        log.info(f"Generate all proof blobs")
        commit_block_numberAlice, commit_block_indexAlice = self.chain.chain.get_tx_position(commit_tx_objectAlice)
        commit_block_numberBob, commit_block_indexBob = self.chain.chain.get_tx_position(commit_tx_objectBob)
        commit_block_numberCharlie, commit_block_indexCharlie = self.chain.chain.get_tx_position(commit_tx_objectCharlie)

        commit_proof_blobAlice = self._generate_proof_block_wrapper(
            commit_block_numberAlice, commit_block_indexAlice, commit_tx_objectAlice, ALICE_ADDRESS)
        commit_proof_blobBob = self._generate_proof_block_wrapper(
            commit_block_numberBob, commit_block_indexBob, commit_tx_objectBob, BOB_ADDRESS)
        commit_proof_blobCharlie = self._generate_proof_block_wrapper(
            commit_block_numberCharlie, commit_block_indexCharlie, commit_tx_objectCharlie, CHARLIE_ADDRESS)

        log.info(f"Generate unsigned tx for reveal")
        unlock_tx_unsigned_rlpAlice = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoAlice)
        unlock_tx_unsigned_rlpBob = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoBob)
        unlock_tx_unsigned_rlpCharlie = self._generate_unsigned_tx(unlock_tx_info=unlock_tx_infoCharlie)
        _unlockExtraData = b''

        log.info(f"Send Alice reveal tx at block {self.chain.head_state.block_number}")
        self.chicken_contract.reveal(
            commit_block_numberAlice,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessAlice),  # bytes32 _witness,
            unlock_tx_unsigned_rlpAlice,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobAlice,  # bytes _proofBlob
            sender=ALICE_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Bob reveal tx at block {self.chain.head_state.block_number}")
        self.chicken_contract.reveal(
            commit_block_numberBob,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessBob),  # bytes32 _witness,
            unlock_tx_unsigned_rlpBob,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobBob,  # bytes _proofBlob
            sender=BOB_PRIVATE_KEY)
        self.chain.mine(1)

        log.info(f"Send Charlie reveal tx at block {self.chain.head_state.block_number}")
        self.chicken_contract.reveal(
            commit_block_numberCharlie,  # uint32 _commitBlockNumber,
            _unlockExtraData,  # bytes _commitData,
            rec_bin(witnessCharlie),  # bytes32 _witness,
            unlock_tx_unsigned_rlpCharlie,  # bytes _rlpUnlockTxUnsigned,
            commit_proof_blobCharlie,  # bytes _proofBlob
            sender=CHARLIE_PRIVATE_KEY)
        self.chain.mine(1)

        ####################################
        ## BROADCAST UNLOCK
        ####################################

        log.info(f"Broadcast unlock for all players")
        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectAlice)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectBob)

        self.chain.mine(1)
        self.chain.direct_tx(unlock_tx_objectCharlie)
        self.chain.mine(1)

        #################################################
        # Select winner
        #################################################
        log.info(f"Fast forward to the end of reveal period and select winner")
        self.chain.mine(REVEAL_PERIOD_LENGTH)
        self.chicken_contract.selectWinner(rec_bin(endCommitBlockRaw), sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.chain.mine(1)
        self.assertTrue(self.chicken_contract.winnerSelected())

        log.info(f"Validate no winner was selected")
        self.assertEqual(0, int(self.chicken_contract.winningSubmarineId().hex()))

        #######################################################
        # END GAME
        #######################################################
        log.info(f"finalize game by all players")
        self.chicken_contract.finalize(rec_bin(commitAlice), sender=ALICE_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitBob), sender=BOB_PRIVATE_KEY)
        self.chicken_contract.finalize(rec_bin(commitCharlie), sender=CHARLIE_PRIVATE_KEY)


    def _create_unlock_transaction(self, unlock_tx_infoAlice):
        return transactions.Transaction(
            int.from_bytes(unlock_tx_infoAlice[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_infoAlice[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_infoAlice[2], byteorder="big"),  # startgas
            unlock_tx_infoAlice[3],  # to addr
            int.from_bytes(unlock_tx_infoAlice[4], byteorder="big"),  # value
            unlock_tx_infoAlice[5],  # data
            int.from_bytes(unlock_tx_infoAlice[6], byteorder="big"),  # v
            int.from_bytes(unlock_tx_infoAlice[7], byteorder="big"),  # r
            int.from_bytes(unlock_tx_infoAlice[8], byteorder="big")  # s
        )

    def _generate_proof_block_wrapper(self, commit_block_number, commit_block_index, commit_tx_object, address):
        commit_block_object = self.chain.chain.get_block_by_number(commit_block_number)
        proveth_expected_block_format_dict = dict()
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
        transactions = []
        for idx, transaction in enumerate(commit_block_object.transactions):
            transactions += [{
                "blockHash": commit_block_object.hash,
                "blockNumber": str(hex((commit_block_object['number']))),
                "from": checksum_encode(transaction.sender),
                "gas": str(hex(transaction['startgas'])),
                "gasPrice": str(hex(transaction['gasprice'])),
                "hash": rec_hex(transaction['hash']),
                "input": rec_hex(transaction['data']),
                "nonce": str(hex(transaction['nonce'])),
                "to": checksum_encode(transaction['to']),
                "transactionIndex": str(hex(idx)),
                "value": str(hex(transaction['value'])),
                "v": str(hex(transaction['v'])),
                "r": str(hex(transaction['r'])),
                "s": str(hex(transaction['s']))
            }]
        proveth_expected_block_format_dict['transactions'] = transactions

        return generate_proof_blob(proveth_expected_block_format_dict, commit_block_index)

    def _generate_unsigned_tx(self, unlock_tx_info):
        unlock_tx_unsigned_object = transactions.UnsignedTransaction(
            int.from_bytes(unlock_tx_info[0], byteorder="big"),  # nonce;
            int.from_bytes(unlock_tx_info[1], byteorder="big"),  # gasprice
            int.from_bytes(unlock_tx_info[2], byteorder="big"),  # startgas
            unlock_tx_info[3],  # to addr
            int.from_bytes(unlock_tx_info[4], byteorder="big"),  # value
            unlock_tx_info[5],  # data
        )
        return rlp.encode(unlock_tx_unsigned_object, transactions.UnsignedTransaction)

if __name__ == "__main__":
    unittest.main()
