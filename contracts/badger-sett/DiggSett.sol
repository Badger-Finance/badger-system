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

        /// Get the shares directly from the current digg strategy, as the controller does not have a wrapper function for digg shares
        address strategy = IController(controller).strategies(address(token));
        uint256 strategyShares = IDiggStrategy(strategy).sharesOf();

        return strategyShares.add(settShares);
    }

    /// @notice Defines how much of the Setts' underlying can be borrowed by the Strategy for use
    /// @notice Custom logic in here for how much the vault allows to be borrowed
    /// @notice Sets minimum required on-hand to keep small withdrawals cheap
    function available() public override view returns (uint256) {
        return IDigg(address(token)).sharesOf(address(this)).div(max).mul(min);
    }

    /// ===== Internal Implementations =====

    /// @dev Calculate the number of shares to issue for a given deposit
    /// @dev This is based on the realized value of underlying assets between Sett & associated Strategy
    function _deposit(uint256 _amount) internal override {
        IDigg digg = IDigg(address(token));

        uint256 _pool = shares(); // Shares realized in system before transfer
        uint256 _before = digg.sharesOf(address(this));

        digg.transferFrom(msg.sender, address(this), _amount);

        uint256 _after = digg.sharesOf(address(this));
        uint256 _sharesTransferred = _after.sub(_before); // Additional check for deflationary tokens

        uint256 sharesToMint = 0;
        if (totalSupply() == 0) {
            sharesToMint = _sharesTransferred;
        } else {
            sharesToMint = (_sharesTransferred.mul(totalSupply())).div(_pool);
        }

        _mint(msg.sender, sharesToMint);
    }

    // No rebalance implementation for lower fees and faster swaps
    function _withdraw(uint256 _shares) internal override {
        IDigg digg = IDigg(address(token));

        uint256 diggSharesToRedeem = (shares().mul(_shares)).div(totalSupply());
        _burn(msg.sender, _shares);

        // Check balance
        uint256 diggSharesInSett = digg.sharesOf(address(this));

        if (diggSharesInSett < diggSharesToRedeem) {
            uint256 _toWithdraw = diggSharesToRedeem.sub(diggSharesInSett);
            IController(controller).withdraw(address(token), _toWithdraw);

            uint256 diggSharesInSettAfterWithdraw = digg.sharesOf(address(this));
            uint256 _diff = diggSharesInSettAfterWithdraw.sub(diggSharesInSett);

            // If we are not able to get the full amount requested from the strategy due to losses, redeem what we can
            if (_diff < _toWithdraw) {
                diggSharesToRedeem = diggSharesInSett.add(_diff);
            }
        }

        // Transfer the corresponding number of tokens to recipient
        digg.transfer(msg.sender, digg.sharesToFragments(diggSharesToRedeem));
    }
}
