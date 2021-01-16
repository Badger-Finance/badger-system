// SP-License-upgradeable-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/digg/IDigg.sol";
import "./MerkleDistributor.sol";

/* ===== DiggDistributor =====
    Variant on MerkleDistributor that encodes claimable values in DIGG shares, rather than balances
    This means the value claimable will remain constant through rebases

    After a preset delay, an owner can recall unclaimed DIGG to the treasury
*/
contract DiggDistributor is MerkleDistributor, OwnableUpgradeable {
    address public rewardsEscrow;
    uint256 public reclaimAllowedTimestamp;

    function initialize(
        address token_,
        bytes32 merkleRoot_,
        address rewardsEscrow_,
        uint256 reclaimAllowedTimestamp_
    ) public initializer {
        __MerkleDistributor_init(token_, merkleRoot_);
        __Ownable_init();
        rewardsEscrow = rewardsEscrow_;
        reclaimAllowedTimestamp = reclaimAllowedTimestamp_;
    }

    function claim(
        uint256 index,
        address account,
        uint256 shares,
        bytes32[] calldata merkleProof
    ) external virtual override {
        require(!isClaimed(index), "DiggDistributor: Drop already claimed.");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, account, shares));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "DiggDistributor: Invalid proof.");

        // Mark it claimed and send the token.
        _setClaimed(index);
        require(IDigg(token).transfer(account, IDigg(token).sharesToFragments(shares)), "DiggDistributor: Transfer failed.");

        emit Claimed(index, account, shares);
    }

    /// ===== Gated Actions: Owner =====

    /// @notice Transfer unclaimed funds to rewards escrow
    function reclaim() external onlyOwner {
        require(now >= reclaimAllowedTimestamp, "DiggDistributor: Before reclaim timestamp");
        uint256 remainingBalance = IDigg(token).balanceOf(address(this));
        IERC20Upgradeable(token).transfer(rewardsEscrow, remainingBalance);
    }
}
