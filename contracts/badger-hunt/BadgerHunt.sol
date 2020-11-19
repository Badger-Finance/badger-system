// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/IMerkleDistributor.sol";
import "./MerkleDistributor.sol";

contract BadgerHunt is MerkleDistributor {
    using SafeMathUpgradeable for uint256;
    uint256 public constant MAX_BPS = 10000;

    uint256 public claimsStart;
    uint256 public gracePeriod;

    uint256 public epochDuration;
    uint256 public rewardReductionPerEpoch;
    uint256 public currentRewardRate;

    address public rewardsEscrow;

    event Hunt(uint256 index, address indexed account, uint256 amount, uint256 userClaim, uint256 rewardsEscrowClaim);

    function initialize(
        address token_,
        bytes32 merkleRoot_,
        uint256 epochDuration_,
        uint256 rewardReductionPerEpoch_,
        uint256 claimsStart_,
        uint256 gracePeriod_,
        address rewardsEscrow_
    ) public initializer {
        __MerkleDistributor_init(token_, merkleRoot_);

        epochDuration = epochDuration_;
        rewardReductionPerEpoch = rewardReductionPerEpoch_;
        claimsStart = claimsStart_;
        gracePeriod = gracePeriod_;

        rewardsEscrow = rewardsEscrow_;

        currentRewardRate = 10000;
    }

    /// ===== View Functions =====

    function getNextEpochStart() public view returns (uint256) {
        uint256 gracePeriodEnd = claimsStart.add(gracePeriod);
        uint256 epoch = getCurrentEpoch();

        if (epoch == 0) {
            return claimsStart.add(gracePeriod);
        } else {
            return claimsStart.add(gracePeriod).add(epochDuration.mul(epoch));
        }
    }

    function getCurrentEpoch() public view returns (uint256) {
        uint256 gracePeriodEnd = claimsStart.add(gracePeriod);

        if (now < gracePeriodEnd) {
            return 0;
        }
        uint256 secondsPastGracePeriod = now.sub(gracePeriodEnd);
        return (secondsPastGracePeriod / epochDuration).add(1);
    }

    function getCurrentRewardsRate() public view returns (uint256) {
        uint256 epoch = getCurrentEpoch();
        if (epoch == 0) return MAX_BPS;
        if (epoch > 4) return 0;
        else return MAX_BPS.sub(epoch.mul(rewardReductionPerEpoch));
    }

    /// ===== Public Actions =====

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

        uint256 claimable = amount.mul(getCurrentRewardsRate()).div(MAX_BPS);

        require(IERC20Upgradeable(token).transfer(account, claimable), "Transfer to user failed.");

        // Transfer any remainder to rewards escrow
        if (claimable != amount) {
            require(IERC20Upgradeable(token).transfer(rewardsEscrow, claimable), "Transfer to rewardsEscrow failed.");
        }

        emit Hunt(index, account, amount, claimable, amount.sub(claimable));
    }
}
