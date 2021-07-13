pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";

import "interfaces/badger/IController.sol";
import "interfaces/digg/IDigg.sol";
import "interfaces/digg/IDiggStrategy.sol";
import "contracts/badger-sett/SettV3.sol";

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

/*
    Stabilize Modification
    Strategy now holds both wbtc and digg. Balance of wbtc is expressed as digg equivalent via strategy
    Switched from shares to fragments for digg for easier readability
*/

interface StabilizeDiggStrategy {
    function balanceOf() external view returns (uint256); // Returns DIGG and DIGG equivalent of strategy, not normalized

    function getTokenAddress(uint256) external view returns (address); // Get the token addresses involved in the strategy
}

contract StabilizeDiggSett is SettV3 {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    function balance() public override view returns (uint256) {
        return balanceOfDiggEquivalentInSettAndStrategy();
    }

    function balanceOfDiggEquivalentInSettAndStrategy() public view returns (uint256) {
        // This will take our strategy and calculate how much digg equivalent we have in wBTC value, normalized to 1e18
        uint256 _diggAmount = 0; // This will be normalized to 1e18
        ERC20Upgradeable diggToken = ERC20Upgradeable(address(token));
        address strategy = IController(controller).strategies(address(token));
        StabilizeDiggStrategy strat = StabilizeDiggStrategy(strategy);

        _diggAmount = diggToken.balanceOf(address(this));
        if (strategy != address(0)) {
            _diggAmount = _diggAmount.add(strat.balanceOf()); // The strategy will automatically convert wbtc to digg equivalent
        }
        uint256 decimals = uint256(diggToken.decimals());
        _diggAmount = _diggAmount.mul(1e18).div(10**decimals); // Normalize the Digg amount

        return _diggAmount;
    }

    function getPricePerFullShare() public override view returns (uint256) {
        if (totalSupply() == 0) {
            return 1e18;
        }
        return balanceOfDiggEquivalentInSettAndStrategy().mul(1e18).div(totalSupply());
    }

    /// ===== Internal Implementations =====

    /// @dev Calculate the number of bDIGG shares to issue for a given deposit
    /// @dev This is based on the realized value of underlying assets between Sett & associated Strategy
    function _deposit(uint256 _amount) internal override {
        require(_amount > 0, "Nothing to deposit");
        IDigg digg = IDigg(address(token));
        uint256 _decimals = uint256(ERC20Upgradeable(address(token)).decimals());

        uint256 _poolBefore = balanceOfDiggEquivalentInSettAndStrategy(); // Normalized digg amount and equivalent in system before transfer
        uint256 _before = digg.balanceOf(address(this));

        require(digg.transferFrom(msg.sender, address(this), _amount));

        uint256 _after = digg.balanceOf(address(this));
        uint256 _diggTransferred = _after.sub(_before); // Additional check for deflationary tokens

        uint256 normalizedAmount = _diggTransferred.mul(1e18).div(10**_decimals); // Convert to bDigg/normalized units
        uint256 bDiggToMint = normalizedAmount;
        if (totalSupply() > 0) {
            // There is already a balance here, calculate our share
            bDiggToMint = normalizedAmount.mul(totalSupply()).div(_poolBefore); // Our share of the total
        }

        _mint(msg.sender, bDiggToMint);
    }

    // No rebalance implementation for lower fees and faster swaps
    function _withdraw(uint256 _bDiggToBurn) internal override {
        require(_bDiggToBurn > 0, "Nothing to withdraw");
        IDigg digg = IDigg(address(token));
        uint256 _decimals = uint256(ERC20Upgradeable(address(token)).decimals());

        uint256 _diggToRedeem = balanceOfDiggEquivalentInSettAndStrategy().mul(_bDiggToBurn).div(totalSupply());
        _diggToRedeem = _diggToRedeem.mul(10**_decimals).div(1e18); // Convert from normalized units to digg units

        _burn(msg.sender, _bDiggToBurn);

        // Check balance
        uint256 _diggInSett = digg.balanceOf(address(this));

        // If we don't have sufficient idle want in Sett, withdraw from Strategy
        if (_diggInSett < _diggToRedeem) {
            uint256 _toWithdraw = _diggToRedeem.sub(_diggInSett);

            // Note: This amount is a DIGG value in the withdraw function
            IController(controller).withdraw(address(token), _toWithdraw);

            uint256 _diggAfterWithdraw = digg.balanceOf(address(this));
            uint256 _diff = _diggAfterWithdraw.sub(_diggInSett);

            // If we are not able to get the full amount requested from the strategy due to losses, redeem what we can
            // This situation should not happen
            if (_diff < _toWithdraw) {
                _diggToRedeem = _diggInSett.add(_diff);
            }
        }

        // Transfer the corresponding number of Digg to recipient
        digg.transfer(msg.sender, _diggToRedeem);
    }
}
