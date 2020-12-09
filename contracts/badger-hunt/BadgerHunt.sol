// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/IMerkleDistributor.sol";
import "./MerkleDistributor.sol";

contract BadgerHunt is MerkleDistributor, OwnableUpgradeable {
    using SafeMathUpgradeable for uint256;
    uint256 public constant MAX_BPS = 10000;

    uint256 public claimsStart;
    uint256 public gracePeriod;

    uint256 public epochDuration;
    uint256 public rewardReductionPerEpoch;
    uint256 public currentRewardRate;
    uint256 public finalEpoch;

    address public rewardsEscrow;

    event Hunt(uint256 index, address indexed account, uint256 amount, uint256 userClaim, uint256 rewardsEscrowClaim);

    function initialize(
        address token_,
        bytes32 merkleRoot_,
        uint256 epochDuration_,
        uint256 rewardReductionPerEpoch_,
        uint256 claimsStart_,
        uint256 gracePeriod_,
        address rewardsEscrow_,
        address owner_
    ) public initializer {
        __MerkleDistributor_init(token_, merkleRoot_);

        __Ownable_init();
        transferOwnership(owner_);

        epochDuration = epochDuration_;
        rewardReductionPerEpoch = rewardReductionPerEpoch_;
        claimsStart = claimsStart_;
        gracePeriod = gracePeriod_;

        rewardsEscrow = rewardsEscrow_;

        currentRewardRate = 10000;

        finalEpoch = (currentRewardRate / rewardReductionPerEpoch_) - 1;
    }

    /// ===== View Functions =====
    /// @dev Get grace period end timestamp
    function getGracePeriodEnd() public view returns (uint256) {
        return claimsStart.add(gracePeriod);
    }

    /// @dev Get claims start timestamp
    function getClaimsStartTime() public view returns (uint256) {
        return claimsStart;
    }

    /// @dev Get the next epoch start
    function getNextEpochStart() public view returns (uint256) {
        uint256 epoch = getCurrentEpoch();

        if (epoch == 0) {
            return getGracePeriodEnd();
        } else {
            return getGracePeriodEnd().add(epochDuration.mul(epoch));
        }
    }

    function getTimeUntilNextEpoch() public view returns (uint256) {
        uint256 epoch = getCurrentEpoch();

        if (epoch == 0) {
            return getGracePeriodEnd().sub(now);
        } else {
            return (getGracePeriodEnd().add(epochDuration.mul(epoch))).sub(now);
        }
    }

    /// @dev Get the current epoch number
    function getCurrentEpoch() public view returns (uint256) {
        uint256 gracePeriodEnd = claimsStart.add(gracePeriod);

        if (now < gracePeriodEnd) {
            return 0;
        }
        uint256 secondsPastGracePeriod = now.sub(gracePeriodEnd);
        return (secondsPastGracePeriod / epochDuration).add(1);
    }

    /// @dev Get the rewards % of current epoch
    function getCurrentRewardsRate() public view returns (uint256) {
        uint256 epoch = getCurrentEpoch();
        if (epoch == 0) return MAX_BPS;
        if (epoch > finalEpoch) return 0;
        else return MAX_BPS.sub(epoch.mul(rewardReductionPerEpoch));
    }

    /// @dev Get the rewards % of following epoch
    function getNextEpochRewardsRate() public view returns (uint256) {
        uint256 epoch = getCurrentEpoch().add(1);
        if (epoch == 0) return MAX_BPS;
        if (epoch > finalEpoch) return 0;
        else return MAX_BPS.sub(epoch.mul(rewardReductionPerEpoch));
    }

    /// ===== Public Actions =====

    function claim(
        uint256 index,
        address account,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) external virtual override {
        require(now >= claimsStart, "BadgerDistributor: Before claim start.");
        require(account == msg.sender, "BadgerDistributor: Can only claim for own account.");
        require(getCurrentRewardsRate() > 0, "BadgerDistributor: Past rewards claim period.");
        require(!isClaimed(index), "BadgerDistributor: Drop already claimed.");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, account, amount));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "BadgerDistributor: Invalid proof.");

        // Mark it claimed and send the token.
        _setClaimed(index);

        require(getCurrentRewardsRate() <= MAX_BPS, "Excessive Rewards Rate");
        uint256 claimable = amount.mul(getCurrentRewardsRate()).div(MAX_BPS);

        require(IERC20Upgradeable(token).transfer(account, claimable), "Transfer to user failed.");
        emit Hunt(index, account, amount, claimable, amount.sub(claimable));
    }

    /// ===== Gated Actions: Owner =====

    /// @notice After hunt is complete, transfer excess funds to rewardsEscrow
    function recycleExcess() external onlyOwner {
        require(getCurrentRewardsRate() == 0 && getCurrentEpoch() > finalEpoch, "Hunt period not finished");
        uint256 remainingBalance = IERC20Upgradeable(token).balanceOf(address(this));
        IERC20Upgradeable(token).transfer(rewardsEscrow, remainingBalance);
    }

    function setGracePeriod(uint256 duration) external onlyOwner {
        gracePeriod = duration;
    }
}
