// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface IProxyAdmin {
    function owner() external view returns (address);

    function transferOwnership(address newOwner) external;

    /**
     * @dev Returns the current implementation of a proxy.
     * This is needed because only the proxy admin can query it.
     * @return The address of the current implementation of the proxy.
     */
    function getProxyImplementation(address proxy) external view returns (address);

    /**
     * @dev Returns the admin of a proxy. Only the admin can query it.
     * @return The address of the current admin of the proxy.
     */
    function getProxyAdmin(address proxy) external view returns (address);

    /**
     * @dev Changes the admin of a proxy.
     * @param proxy Proxy to change admin.
     * @param newAdmin Address to transfer proxy administration to.
     */
    function changeProxyAdmin(address proxy, address newAdmin) external;

    /**
     * @dev Upgrades a proxy to the newest implementation of a contract.
     * @param proxy Proxy to be upgraded.
     * @param implementation the address of the Implementation.
     */
    function upgrade(address proxy, address implementation) external;

    /**
     * @dev Upgrades a proxy to the newest implementation of a contract and forwards a function call to it.
     * This is useful to initialize the proxied contract.
     * @param proxy Proxy to be upgraded.
     * @param implementation Address of the Implementation.
     * @param data Data to send as msg.data in the low level call.
     * It should include the signature and the parameters of the function to be called, as described in
     * https://solidity.readthedocs.io/en/v0.4.24/abi-spec.html#function-selector-and-argument-encoding.
     */
    function upgradeAndCall(
        address proxy,
        address implementation,
        bytes memory data
    ) external payable;
}
