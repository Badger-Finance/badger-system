// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

contract DiggTreasury is OwnableUpgradeable {
    using SafeERC20Upgradeable for ERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    ERC20Upgradeable public constant digg = ERC20Upgradeable(address(0x798D1bE841a82a273720CE31c822C61a67a601C3));
    ERC20Upgradeable public constant wbtc = ERC20Upgradeable(address(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599));

    address public approvedRecipient;

    function initialize(address recipient_) external initializer {
        __Ownable_init();
        approvedRecipient = recipient_;
    }

    modifier onlyApprovedRecipient() {
        require(msg.sender == approvedRecipient, "onlyApprovedRecipient");
        _;
    }

    /// @dev Exchange specified amount of WBTC for DIGG
    /// @dev This relies completely on trust in the logic of the approvedRecipient
    /// @dev Recipient is locked to approvedRecipient as additonal security measure
    function exchangeWBTCForDigg(
        uint256 wbtcIn, // wBTC that we are sending to the treasury exchange
        uint256 diggOut, // digg that we are requesting from the treasury exchange
        address recipient // address to send the digg to, which is this address
    ) external onlyApprovedRecipient {
        wbtc.safeTransferFrom(approvedRecipient, address(this), wbtcIn);
        digg.safeTransfer(approvedRecipient, diggOut);
    }

    function sweep(ERC20Upgradeable token) external onlyOwner {
        token.safeTransfer(owner(), token.balanceOf(address(this)));
    }
}
