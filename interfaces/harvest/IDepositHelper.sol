// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface IDepositHelper {
    
    event DepositComplete(address holder, uint256 numberOfTransfers);

    /*
     * Transfers tokens of all kinds
     */
    function depositAll(uint256[] memory amounts, address[] memory vaultAddresses) external;
}
