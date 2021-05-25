// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";

import "interfaces/badger/IController.sol";
import "interfaces/digg/IDigg.sol";
import "interfaces/digg/IDiggStrategy.sol";
import "./Sett.sol";

/* 
    bDIGG is denominated in scaledShares.
    At the start 1 bDIGG = 1 DIGG (at peg)

    Source: https://github.com/iearn-finance/yearn-protocol/blob/develop/contracts/vaults/yVault.sol
    
    Changelog:

    V1.1
    * Strategist no longer has special function calling permissions
    * Version function added to contract
    * All write functions, with the exception of transfer, are pausable
    * Keeper or governance can pause
    * Only governance can unpause

    V1.2
    * Transfer functions are now pausable along with all other non-permissioned write functions
    * All permissioned write functions, with the exception of pause() & unpause(), are pausable as well
*/
contract DiggSett is Sett {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    function shares() public view returns (uint256) {
        uint256 settShares = IDigg(address(token)).sharesOf(address(this));

        // Get the shares directly from the current digg strategy, as the controller does not have a wrapper function for digg shares
        address strategy = IController(controller).strategies(address(token));
        uint256 strategyShares = IDiggStrategy(strategy).sharesOf();

        return strategyShares.add(settShares);
    }

    function getPricePerFullShare() public override view returns (uint256) {
        if (totalSupply() == 0) {
            return 1e18;
        }
        IDigg digg = IDigg(address(token));
        uint256 scaledShares = digg.sharesToScaledShares(shares());
        return scaledShares.mul(1e18).div(totalSupply());
    }

    /// ===== Internal Implementations =====

    /// @dev Calculate the number of bDIGG shares to issue for a given deposit
    /// @dev This is based on the realized value of underlying assets between Sett & associated Strategy
    function _deposit(uint256 _amount) internal override {
        IDigg digg = IDigg(address(token));

        uint256 _poolBefore = shares(); // Shares realized in system before transfer
        uint256 _before = digg.sharesOf(address(this));

        require(digg.transferFrom(msg.sender, address(this), _amount));

        uint256 _after = digg.sharesOf(address(this));
        uint256 _sharesTransferred = _after.sub(_before); // Additional check for deflationary tokens

        uint256 bDiggToMint = 0;
        if (totalSupply() == 0) {
            bDiggToMint = digg.sharesToScaledShares(_sharesTransferred);
        } else {
            uint256 _poolBeforeScaled = digg.sharesToScaledShares(_poolBefore);
            uint256 _sharesTransferredScaled = digg.sharesToScaledShares(_sharesTransferred);
            bDiggToMint = _sharesTransferredScaled.mul(totalSupply()).div(_poolBeforeScaled);
        }

        _mint(msg.sender, bDiggToMint);
    }

    // No rebalance implementation for lower fees and faster swaps
    function _withdraw(uint256 _bDiggToBurn) internal override {
        IDigg digg = IDigg(address(token));

        // uint256 _sharesToRedeem = (shares().mul(_bDiggToBurn)).div(totalSupply());
        uint256 _sharesToRedeem = (shares().div(totalSupply())).mul(_bDiggToBurn);

        _burn(msg.sender, _bDiggToBurn);

        // Check balance
        uint256 _sharesInSett = digg.sharesOf(address(this));

        // If we don't have sufficient idle want in Sett, withdraw from Strategy
        if (_sharesInSett < _sharesToRedeem) {
            uint256 _toWithdraw = _sharesToRedeem.sub(_sharesInSett);

            // Note: This amount is scaled as a DIGG value in the withdraw function
            IController(controller).withdraw(address(token), digg.sharesToFragments(_toWithdraw));

            uint256 _sharesAfterWithdraw = digg.sharesOf(address(this));
            uint256 _diff = _sharesAfterWithdraw.sub(_sharesInSett);

            // If we are not able to get the full amount requested from the strategy due to losses, redeem what we can
            if (_diff < _toWithdraw) {
                _sharesToRedeem = _sharesInSett.add(_diff);
            }
        }

        // Transfer the corresponding number of shares, scaled to DIGG fragments, to recipient
        digg.transfer(msg.sender, digg.sharesToFragments(_sharesToRedeem));
    }
}
