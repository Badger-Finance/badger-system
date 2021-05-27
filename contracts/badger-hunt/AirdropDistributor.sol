// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/digg/IDigg.sol";
import "./MerkleDistributor.sol";

/* ===== AirdropDistributor =====
    Variant on MerkleDistributor that encodes claimable values in DIGG amount, rather than balances
    This means the value claimable will remain constant through rebases

    After a preset delay, an owner can recall unclaimed DIGG to the treasury
*/
contract AirdropDistributor is MerkleDistributor, OwnableUpgradeable, PausableUpgradeable {
    address public rewardsEscrow;
    uint256 public reclaimAllowedTimestamp;
    bool public isOpen;

    mapping(address => bool) public isClaimTester;

    function initialize(
        address token_,
        bytes32 merkleRoot_,
        address rewardsEscrow_,
        uint256 reclaimAllowedTimestamp_,
        address[] memory claimTesters_
    ) public initializer whenNotPaused {
        __MerkleDistributor_init(token_, merkleRoot_);
        __Ownable_init();
        __Pausable_init_unchained();
        rewardsEscrow = rewardsEscrow_;
        reclaimAllowedTimestamp = reclaimAllowedTimestamp_;
        isOpen = false;

        for (uint256 i = 0; i < claimTesters_.length; i++) {
            isClaimTester[claimTesters_[i]] = true;
        }

        // Paused on launch
        _pause();
    }

    function claim(
        uint256 index,
        address account,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) external virtual override whenNotPaused {
        require(!isClaimed(index), "AirdropDistributor: Drop already claimed.");

        // Only test accounts can claim before launch
        if (isOpen == false) {
            _onlyClaimTesters(msg.sender);
        }

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, account, amount));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "AirdropDistributor: Invalid proof.");

        // Mark it claimed and send the token.
        _setClaimed(index);
        require(IDigg(token).transfer(account, amount), "AirdropDistributor: Transfer failed.");

        emit Claimed(index, account, amount);
    }

    /// ===== Gated Actions: Owner =====

    /// @notice Transfer unclaimed funds to rewards escrow
    function reclaim() external onlyOwner whenNotPaused {
        require(now >= reclaimAllowedTimestamp, "AirdropDistributor: Before reclaim timestamp");
        uint256 remainingBalance = IDigg(token).balanceOf(address(this));
        require(IERC20Upgradeable(token).transfer(rewardsEscrow, remainingBalance), "AirdropDistributor: Reclaim failed");
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function openAirdrop() external onlyOwner whenNotPaused {
        isOpen = true;
    }

    /// ===== Internal Helper Functions =====
    function _onlyClaimTesters(address account) internal view {
        require(isClaimTester[account], "onlyClaimTesters");
    }
}
