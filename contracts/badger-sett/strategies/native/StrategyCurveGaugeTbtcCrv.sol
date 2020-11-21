// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "./StrategyCurveGaugeBase.sol";

contract StrategyCurveGaugeTbtcCrv is StrategyCurveGaugeBase {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    /// ===== Internal Helper Functions =====

    /// @dev Expects lpComponent to be wBTC
    function _add_liquidity_curve(uint256 _amount) internal override {
        ICurveFi(curveSwap).add_liquidity([0, 0, _amount, 0], 0);
    }
}
