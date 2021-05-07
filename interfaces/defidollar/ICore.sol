// SPDX-License-Identifier: MIT

pragma solidity 0.6.11;

interface ICore {
    function mint(
        uint256 btc,
        address account,
        bytes32[] calldata merkleProof
    ) external returns (uint256);

    function redeem(uint256 btc, address account) external returns (uint256);

    function btcToBbtc(uint256 btc) external view returns (uint256, uint256);

    function bBtcToBtc(uint256 bBtc) external view returns (uint256 btc, uint256 fee);

    function pricePerShare() external view returns (uint256);

    function setGuestList(address guestlist) external;

    function owner() external view returns (address);
}
