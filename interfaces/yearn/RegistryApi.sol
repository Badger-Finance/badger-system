// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0 <0.7.0;

interface RegistryAPI {
    function governance() external view returns (address);

    function latestVault(address token) external view returns (address);

    function numVaults(address token) external view returns (uint256);

    function vaults(address token, uint256 deploymentId) external view returns (address);
}
