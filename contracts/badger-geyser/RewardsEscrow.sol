// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "contracts/badger-timelock/ExecutorOnlyCall.sol";

/**
 * @title A holder of tokens to be distributed via a Geyser.
 * Used in cases when a staking asset address is not known at the time of staking geyser creation.
 * Owner must be trusted to set the correct staking asset and distribute the tokens to the geyser.
 */
contract RewardsEscrow is OwnableUpgradeable, ReentrancyGuardUpgradeable, ExecutorOnlyCall {
    mapping(address => bool) public isApproved;

    event Approve(address recipient);
    event RevokeApproval(address recipient);
    event Call(address to, uint256 value, bytes data);

    function initialize() public initializer {
        __Ownable_init();
        __ReentrancyGuard_init_unchained();
    }

    /// ===== Modifiers =====
    function _onlyApprovedRecipients(address recipient) internal view {
        require(isApproved[recipient] == true, "Recipient not approved");
    }

    /// ===== Permissioned Functions: Owner =====

    function approveRecipient(address recipient) external onlyOwner {
        isApproved[recipient] = true;
        emit Approve(recipient);
    }

    function revokeRecipient(address recipient) external onlyOwner {
        isApproved[recipient] = false;
        emit RevokeApproval(recipient);
    }

    /**
     * @notice Allows the timelock to call arbitrary contracts, as long as it does not reduce it's locked token balance
     * @dev Initialization check is implicitly provided by `voteExists()` as new votes can only be
     *      created via `newVote(),` which requires initialization
     * @param to Contract address to call
     * @param value ETH value to send, if any
     * @param data Encoded data to send
     */
    function call(
        address to,
        uint256 value,
        bytes calldata data
    ) external payable onlyOwner nonReentrant() returns (bool success) {
        _onlyApprovedRecipients(to);
        success = execute(to, value, data, gasleft());
        emit Call(to, value, data);
    }

    /// @notice Send tokens to a distribution pool
    function transfer(
        address token,
        address recipient,
        uint256 amount
    ) external onlyOwner {
        _onlyApprovedRecipients(recipient);
        IERC20Upgradeable(token).transfer(recipient, amount);
    }

    function signalTokenLock(
        address geyser,
        address token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime
    ) external onlyOwner {
        _onlyApprovedRecipients(geyser);
        IBadgerGeyser(geyser).signalTokenLock(token, amount, durationSec, startTime);
    }
}
