pragma solidity ^0.5.0;

import "./LibSubmarineSimple.sol";
import "./openzeppelin-solidity/contracts/math/SafeMath.sol";
import "./openzeppelin-solidity/contracts/token/ERC721/IERC721.sol";
import "./openzeppelin-solidity/contracts/token/ERC721/IERC721Receiver.sol";

contract ChickenSubmarine is LibSubmarineSimple {
    using SafeMath for uint256; //prevents overflow

    
    address payable public manager;
    bool public isInitiated;
    
    mapping (bytes32 => address payable) public players; //players[_submarineId] gives us the address of the player
    bytes32[] public revealedSubmarines;
    bytes32 public winningSubmarineId;
    bool public winnerSelected;
    
    uint96 public minBet;
    
    uint32 public startBlock;
    uint32 public endCommitBlock;
    bytes32 public endCommitBlockCrypt;
    uint32 public startRevealBlock;
    uint32 public endRevealBlock;
    
    
    constructor() public {
        isInitiated = false;
        winnerSelected = false; //makes sure winner is selected once within a game
        manager = msg.sender;
    }


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
        endRevealBlock = _StartBlock + 180; // margine for proveth, starting from start block
        
        endCommitBlockCrypt = _endCommitBlockCrypt; //promise for endCommitBlock that is > startBlock & < startRevealBlock

        minBet = _MinBet;
    }

  /*/// @notice This creates the auction.
  function onERC721Received(
    address _operator,
    address _from,
    uint256 _tokenId,
    bytes memory _data
  ) public returns(bytes4) {
    require(address(erc721) == address(0x0));

    // In solidity 0.5.0, we can just do this:
    //(startBlock, startRevealBlock, minBet, endCommitBlockCrypt) = abi.decode(_data, (uint32, uint32, uint256, bytes32));
    // For now, here is some janky assembly hack that does the same thing,
    // only less efficiently.
    require(_data.length == 8);
    bytes memory data = _data; // Copy to memory;
    uint32 tempStartBlock;
    uint32 tempEndBlock;
    assembly {
      tempStartBlock := div(mload(add(data, 32)), exp(2, 224))
      tempEndBlock := and(div(mload(add(data, 32)), exp(2, 192)), 0xffffffff)
    }

    endRevealBlock = startBlock + 180;

    require(block.number < startBlock);
    require(startBlock < startRevealBlock);
    require(minBet != uint256(0));
    erc721 = IERC721(msg.sender);
    erc721TokenId = _tokenId;
    manager = address(uint160(_from));

    return bytes4(keccak256("onERC721Received(address,address,uint256,bytes)"));
  }*/

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
        ); //verify minimimum participation value
        
        players[_submarineId] = msg.sender;
        revealedSubmarines.push(_submarineId);
    }
    
    
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
        
        uint32 closestBlockTime = startBlock;
        //select the winner
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
            //send commition to manager
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
}