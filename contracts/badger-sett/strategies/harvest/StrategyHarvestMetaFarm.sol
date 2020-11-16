// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "../BaseStrategy.sol";

contract StrategyHarvestMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant univ2Router2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Dex
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route
    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address[1] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;

        want = _wantConfig[0];
    }

    function getName() external override pure returns (string memory) {
        return "StrategyHarvestMetaFarm";
    }

    function deposit() override public {
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        emit Deposit(_want, address(0));
    }
    
    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
    }

    /// @notice Withdraw partial funds, normally used with a vault withdrawal
    function withdraw(uint256 _amount) external override {
        _onlyController();
        emit Withdraw(_amount);
    }

    /// @notice Withdraw all funds, normally used when migrating strategies
    function withdrawAll() external override returns (uint256 balance) {
        _onlyController();
        _withdrawAll();
    }

    function _withdrawAll() internal {
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() public override {
        _onlyGovernanceOrStrategist();
    }

    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        return _amount;
    }

    function balanceOfPool() public view returns (uint256) {
        return 0;
    }

    function balanceOf() public view override returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }
}
