// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface ICurveMintr {
    function mint(address) external;

    function minted(address arg0, address arg1) external view returns (uint256);
}
