//SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

interface IMemeLtd {
    function contractURI() external view;

    function balanceOf(address _owner, uint256 _id) external view returns (uint256);

    function mint(
        address _to,
        uint256 _id,
        uint256 _quantity,
        bytes memory _data
    ) external;

    function safeTransferFrom(
        address _from,
        address _to,
        uint256 _id,
        uint256 _amount,
        bytes calldata _data
    ) external;
}
