// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "interfaces/badger/IPausable.sol";
import "contracts/badger-timelock/Executor.sol";

contract GatedProxy is AccessControlUpgradeable, Executor {
    bytes32 public constant APPROVED_ACCOUNT_ROLE = keccak256("APPROVED_ACCOUNT_ROLE");
    event Call(address to, uint256 value, bytes data, uint256 operation);

    function initialize(address initialAdmin_, address initialUser_) external initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
        _setupRole(APPROVED_ACCOUNT_ROLE, initialUser_);
    }

    modifier onlyApprovedAccount() {
        require(hasRole(APPROVED_ACCOUNT_ROLE, msg.sender), "onlyApprovedAccount");
        _;
    }

    function pause(address destination) public onlyApprovedAccount {
        IPausable(destination).pause();
    }

    /**
     * @param to Contract address to call
     * @param value ETH value to send, if any
     * @param data Encoded data to send
     * @param operation Call or Delegatecall
     */
    function call(
        address to,
        uint256 value,
        bytes calldata data,
        uint256 operation
    ) external payable onlyApprovedAccount returns (bool success) {
        success = execute(to, value, data, operation, gasleft());
        emit Call(to, value, data, operation);
    }
}
