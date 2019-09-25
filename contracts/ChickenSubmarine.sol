pragma solidity ^0.5.0;

import "./LibSubmarineSimple.sol";
import "./openzeppelin-solidity/contracts/math/SafeMath.sol";

contract ChickenSubmarine is LibSubmarineSimple {
    using SafeMath for uint256; //prevents overflow

    /////////////
    // Storage //
    /////////////

    // The owner of the contract and the creator of the current game
    address payable public manager;
    // Stores player information. players[_submarineId] gives us the address of the player
    mapping (bytes32 => address) public players;
    // Stores the revealed Submarine IDs
    bytes32[] public revealedSubmarines;
    // Stores the winning Submarine ID after selecting the winner
    bytes32 public winningSubmarineId;
    // Flag for monitoring if a winner was selected
    bool public winnerSelected;

    // Stores the minimum bet in Wei for participating in the game
    uint96 public minBet;
    // Stores the block number of when the game starts
    uint32 public startBlock;
    // Stores the selected block number to for the final valid commit in the game,
    // revealed only after initiating SelectWinner
    uint32 public endCommitBlock;
    //Stores the end commit block hash crypt in keccak256
    bytes32 public endCommitBlockCrypt;
    // Stores the block number of the beginning of the reveal period
    uint32 public startRevealBlock;
    // Stores the block number for the last valid reveal in the game, hardcoded to startRevealBlock + 30
    uint32 public endRevealBlock;
    // TODO - delete this param
    bytes32 public kakaBlockNum;


    /**
     * @notice The constructor for deploying a new Chicken game with no parameters
     */
    constructor() public {
        isInitiated = false;
        winnerSelected = false; //makes sure winner is selected once within a game
        manager = msg.sender;
    }


    /**
     * @notice The init function to instantiating a deployed Chicken game
     * @param  _StartBlock The block number from which the game begins and a valid commit can be placed
     * @param  _MinBet The minimum amount in Wei a player must commit to a submarine
     * @param  _endCommitBlockCrypt The end commit block number from which the players cannot commit
                new submarines and the reveal period starts hashed using keccak256
     */
    function initChickenGame(uint32 _StartBlock, uint32 _StartRevealBlock, uint96 _MinBet, bytes32 _endCommitBlockCrypt) public {
        require(
            isInitiated == false,
            "Chicken - Contract can be initiated only once"
        );
        require(
            manager == msg.sender,
            "Chicken - Only contract creator can init Game"
        );
        require(
            block.number < _StartBlock,
            "Chicken - Block number is greater than startBlock"
        );
        require(
            _StartBlock < _StartRevealBlock,
            "Chicken - startBlock is greater than startRevealBlock"
        );
        require(
            _MinBet != uint96(0),
            "Chicken - minimum bet was set to 0"
        );

        startBlock = _StartBlock;
        startRevealBlock = _StartRevealBlock;
        endRevealBlock = _StartRevealBlock + 30; // margine for proveth

        endCommitBlockCrypt = _endCommitBlockCrypt; //promise for endCommitBlock that is > startBlock & < startRevealBlock

        minBet = _MinBet;
    }


    /**
     * @notice onSubmarineReveal implements the game logic for a reveal action made by a player.
     *         Revealer's address & submarine Id are stored in the contract.
     * @param  _submarineId the ID for this submarine workflow
     * @param  _embeddedDAppData unused variable in our game logic
     * @param  _value unused variable in our game logic (we use getSubmarineAmount(_submarineId) instead)
     */
    function onSubmarineReveal(
        bytes32 _submarineId,
        bytes memory _embeddedDAppData,
        uint256 _value
    ) internal {
        require(
            startRevealBlock <= block.number && block.number <= endRevealBlock,
            "Chicken - current block is not in reveal period"
        );
        require(
            _value >= minBet,
            "Chicken - amount sent is less than minimum bet"
        ); //verify minimum participation value

        players[_submarineId] = msg.sender;
        revealedSubmarines.push(_submarineId);
    }


    /**
     * @notice selectWinner is used only by the game's manager.
     *  Winner is selected from within all valid participants after choosing the end of the valid commit period.
     *  Winner Submarine Id is then stored in the contract
     */
    function selectWinner(uint32 _secretCommitBlock) public {
        require(
            msg.sender == manager,
            "Chicken - sender is not game creator"
        );
        require(
            block.number > endRevealBlock,
            "Chicken - reveal period has not ended. can't select winner"
        );
        require(
            winnerSelected == false,
            "Chicken - winner was initialized"
        ); //winner must be un-initialized
        require(
            keccak256(abi.encodePacked(_secretCommitBlock)) == endCommitBlockCrypt,
            "Chicken - secretCommitBlock has different hash"
        );


        endCommitBlock = _secretCommitBlock;
        // promise to reimburse money (should not enter here)
        if(endCommitBlock <= startBlock || endCommitBlock >= startRevealBlock) {
            for (uint j=0; j<revealedSubmarines.length; j++) {
                bytes32 curr_sub = revealedSubmarines[j];
                if (revealedAndUnlocked(curr_sub)) {
                    players[curr_sub].transfer(getSubmarineAmount(curr_sub));
                }
            }
        }

        //select the winner
        uint32 closestBlockTime = startBlock;
        for (uint i=0; i<revealedSubmarines.length; i++) {
            uint32 commitTxBlockNumber = getSubmarineCommitBlockNumber(revealedSubmarines[i]);

            if (startBlock <= commitTxBlockNumber && commitTxBlockNumber <= endCommitBlock) {
                //closest to endCommitBlock wins
                if (commitTxBlockNumber > closestBlockTime) {
                    winningSubmarineId = revealedSubmarines[i];
                    closestBlockTime = commitTxBlockNumber;
                }
                //largest bidder at closestBlockTime wins
                else if (commitTxBlockNumber == closestBlockTime) {
                    if (getSubmarineAmount(revealedSubmarines[i]) > getSubmarineAmount(winningSubmarineId)) {
                        winningSubmarineId = revealedSubmarines[i];
                    }
                    //else (if equal), first revealer wins
                }
            }
        }

        winnerSelected = true;
    }


    /**
     * @notice finalize is called by each player to check whether he is the selected winner
     *  and receive the winner's reward or to receive a partial reimbursement of the participation fee
     * @param _submarineId the ID for this submarine workflow
     */
    function finalize(bytes32 _submarineId) external {
        require(
            block.number > endRevealBlock,
            "Chicken - current block is smaller than end reveal period"
        );
        require(
            _submarineId != bytes32(0),
            "Chicken - submarineId is 0"
        ); // prevent cheating if no winner is selected
        require(
            winnerSelected == true,
            "Chicken - winner was not selected"
        );
        require(
            revealedAndUnlocked(_submarineId),
            "Chicken - submarine is not unlocked"
        );
        require(
            players[_submarineId] == msg.sender,
            "Chicken - sender is not owner of submarine"
        );

        if (winningSubmarineId == bytes32(0) || _submarineId == winningSubmarineId) {
            //send money to winner | or to every participant if no winner was selected
            //send commission to the manager
            msg.sender.transfer(getSubmarineAmount(_submarineId)*95/100);
            manager.transfer(getSubmarineAmount(_submarineId)*5/100);
        } else {
            //send money to winner
            //send consolation prize to looser
            players[winningSubmarineId].transfer(getSubmarineAmount(_submarineId)*5/10);
            msg.sender.transfer(getSubmarineAmount(_submarineId)*45/100);
            manager.transfer(getSubmarineAmount(_submarineId)*5/100);
        }
    }
    function _helper_kaka(uint32 blockNum) public{
        kakaBlockNum = keccak256(abi.encodePacked(blockNum));
    }
}