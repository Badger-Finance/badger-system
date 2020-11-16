// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/cryptography/MerkleProof.sol";
import "interfaces/badger-hunt/IMerkleDistributor.sol";
import "./MerkleDistributor.sol";

/*
    Gamified Merkle Distributor

    * Specified recipient of an amount can claim their tokens at any point
    * After a grace period (specified in constructor), any account can claim the tokens of 
*/
contract BadgerHunt is MerkleDistributor {
    using SafeMath for uint256;
    uint256 public constant MAX_BPS = 10000;

    uint256 public claimsStart;
    uint256 public numClaimEpochs;
    uint256 public epochDuration;
    uint256 public rewardReductionPerEpoch;

    uint256 public currentClaimEpoch;
    uint256 public currentRewardRate;

    uint256 public gracePeriodEnd;
    bytes32 public secretHash;

    constructor(address token_, bytes32 merkleRoot_, uint256 gracePeriodEnd_, bytes32 secretHash_) MerkleDistributor(token_, merkleRoot_) public {
        gracePeriodEnd = gracePeriodEnd_;
        secretHash = secretHash_;

        claimsStart = 0;
        rewardReductionPerEpoch = 2000;
        currentRewardRate = 10000;
    }

    /// @dev Update the current epoch. If after the final epoch end, no need to update
    function _updateEpoch() internal {
        // Ensure we're not in the final epoch
        if (currentClaimEpoch.add(1) < numClaimEpochs) {

        }
    }

    function _getNextEpochStartTime() internal view returns (uint256) {
        return 0;
    }

    function claim(uint256 index, address account, uint256 amount, bytes32[] calldata merkleProof) external override virtual {
        require(!isClaimed(index), 'BadgerDistributor: Drop already claimed.');

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, account, amount));
        require(MerkleProof.verify(merkleProof, merkleRoot, node), 'BadgerDistributor: Invalid proof.');

        // Mark it claimed and send the token.
        _setClaimed(index);

        require(IERC20(token).transfer(account, amount), 'BadgerDistributor: Transfer failed.');
        emit Claimed(index, account, amount);
    }


    /// @dev 
    function claimSecret(uint256 index, address account, uint256 amount, bytes32[] calldata merkleProof, bytes32 secret) external {
        require(keccak256(abi.encode(secret)) == secret);
    }
}
