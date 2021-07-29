// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "./StrategyMStableVaultBase.sol";
import "interfaces/mStable/IMStableImbtc.sol";

/// @title  StrategyMStableVaultImbtc
/// @author mStable
/// @notice Strategy utilising mStable interest bearing BTC
contract StrategyMStableVaultImbtc is StrategyMStableVaultBase {
    /// @dev Mints mStable Asset using a specified input and amount
    /// @param _input Address of asset to be used in the mint
    /// @param _amount Units of _input to mint with
    function _mintWant(address _input, uint256 _amount) internal override {
        // minOut = amountIn * 0.8
        uint256 minted = IMStableAsset(mBTC).mint(_input, _amount, _amount.mul(80).div(100), address(this));
        IMStableImbtc(want).depositSavings(minted);
    }
}
