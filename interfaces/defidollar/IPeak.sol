// SPDX-License-Identifier: MIT

pragma solidity 0.6.11;

interface IPeak {
    function mint(
        uint256 poolId,
        uint256 inAmount,
        bytes32[] calldata merkleProof
    ) external returns (uint256);

    function redeem(uint256 poolId, uint256 inAmount) external returns (uint256);

    function portfolioValue() external view returns (uint256);
}
