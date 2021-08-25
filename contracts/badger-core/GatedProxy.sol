// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "interfaces/badger/IPausable.sol";
import "contracts/badger-timelock/Executor.sol";

contract GatedProxy is AccessControlUpgradeable, Executor {
    bytes32 public constant APPROVED_ACCOUNT_ROLE = keccak256("APPROVED_ACCOUNT_ROLE");
    event Call(address to, uint256 value, bytes data, uint256 operation);

    function initialize(address initialAdmin_, address[] memory initialAccounts_) external initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);

        for (uint256 i = 0; i < initialAccounts_.length; i++) {
            _setupRole(APPROVED_ACCOUNT_ROLE, initialAccounts_[i]);
        }
    }

    modifier onlyApprovedAccount() {
        require(hasRole(APPROVED_ACCOUNT_ROLE, msg.sender), "onlyApprovedAccount");
        _;
    }

    /**
     * @param to Contract address to call
     * @param value ETH value to send, if any
     * @param data Encoded data to send
     * @dev Only calls are supported, not delegatecalls
     */
    function call(
        address to,
        uint256 value,
        bytes calldata data
    ) external payable onlyApprovedAccount returns (bool success) {
        success = execute(to, value, data, 0, gasleft());
        emit Call(to, value, data, 0);
    }
}
