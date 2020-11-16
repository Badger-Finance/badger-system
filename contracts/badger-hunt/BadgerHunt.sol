// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/IMerkleDistributor.sol";
import "./MerkleDistributor.sol";

/*
    Gamified Merkle Distributor

    * Specified recipient of an amount can claim their tokens at any point
    * After a grace period (specified in constructor), any account can claim the tokens of 
*/
contract BadgerHunt is MerkleDistributor {
    using SafeMathUpgradeable for uint256;
    uint256 public constant MAX_BPS = 10000;

    uint256 public claimsStart;
    uint256 public numClaimEpochs;
    uint256 public epochDuration;
    uint256 public rewardReductionPerEpoch;

    uint256 public currentClaimEpoch;
    uint256 public currentRewardRate;

    uint256 public gracePeriodEnd;

    function initialize(
        address token_,
        bytes32 merkleRoot_,
        uint256 epochDuration_,
        uint256 rewardReductionPerEpoch_,
        uint256 claimsStart_
    ) public initializer {
        __MerkleDistributor_init(token_, merkleRoot_);

        epochDuration = epochDuration_;
        rewardReductionPerEpoch = rewardReductionPerEpoch_;
        claimsStart = claimsStart_;

        currentRewardRate = 10000;
    }

    /// @dev Update the current epoch. If after the final epoch end, no need to update
    function _updateEpoch() internal {
        // Ensure we're not in the final epoch
        if (currentClaimEpoch.add(1) < numClaimEpochs) {}
    }

    function _getNextEpochStartTime() internal view returns (uint256) {
        return 0;
    }

    function claim(
        uint256 index,
        address account,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) external virtual override {
        require(!isClaimed(index), "BadgerDistributor: Drop already claimed.");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, account, amount));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "BadgerDistributor: Invalid proof.");

        // Mark it claimed and send the token.
        _setClaimed(index);

        require(IERC20Upgradeable(token).transfer(account, amount), "BadgerDistributor: Transfer failed.");
        emit Claimed(index, account, amount);
    }
}
