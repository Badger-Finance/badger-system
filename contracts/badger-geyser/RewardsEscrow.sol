// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";

/**
 * @title A holder of tokens to be distributed via a Geyser.
 * Used in cases when a staking asset address is not known at the time of staking geyser creation.
 * Owner must be trusted to set the correct staking asset and distribute the tokens to the geyser.
 */
contract RewardsEscrow is OwnableUpgradeable {
    mapping(address => bool) public isApproved;

    event Approve(address recipient);
    event RevokeApproval(address recipient);

    function initialize(address owner_) public initializer {
        __Ownable_init();
        transferOwnership(owner_);
    }

    function approveRecipient(address recipient) external onlyOwner {
        isApproved[recipient] = true;
        emit Approve(recipient);
    }

    function revokeRecipient(address recipient) external onlyOwner {
        isApproved[recipient] = false;
        emit RevokeApproval(recipient);
    }

    /// @notice Add tokens into the distribution pool
    function transfer(
        address token,
        address recipient,
        uint256 amount
    ) external onlyOwner {
        require(isApproved[recipient] == true, "Recipient not approved");
        IERC20Upgradeable(token).transfer(recipient, amount);
    }
}
