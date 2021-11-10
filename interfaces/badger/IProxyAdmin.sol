// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
interface IProxyAdmin {
    /**
     * @dev Returns the current implementation of `proxy`.
     * 
     * Requirements:
     * 
     * - This contract must be the admin of `proxy`.
     */
    function getProxyImplementation(address proxy) external view returns (address);

    /**
     * @dev Returns the current admin of `proxy`.
     * 
     * Requirements:
     * 
     * - This contract must be the admin of `proxy`.
     */
    function getProxyAdmin(address proxy) external view returns (address);

    /**
     * @dev Changes the admin of `proxy` to `newAdmin`.
     * 
     * Requirements:
     * 
     * - This contract must be the current admin of `proxy`.
     */
    function changeProxyAdmin(address proxy, address newAdmin) external;

    /**
     * @dev Upgrades `proxy` to `implementation`. See {address-upgradeTo}.
     * 
     * Requirements:
     * 
     * - This contract must be the admin of `proxy`.
     */
    function upgrade(address proxy, address implementation) external;

    /**
     * @dev Upgrades `proxy` to `implementation` and calls a function on the new implementation. See
     * {address-upgradeToAndCall}.
     * 
     * Requirements:
     * 
     * - This contract must be the admin of `proxy`.
     */
    function upgradeAndCall(address proxy, address implementation, bytes memory data) external;
}
