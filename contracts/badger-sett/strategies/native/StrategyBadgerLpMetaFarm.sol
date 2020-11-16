// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../BaseStrategy.sol";
import "interfaces/badger/IStrategy.sol";

/*
    Strategy to compound badger rewards
    - Deposit Badger into the vault to receive more from a special rewards pool
*/
contract StrategyBadgerLpMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public geyser;

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address[2] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;

        want = _wantConfig[0];
        geyser = _wantConfig[1];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }
     
    /// @notice Deposit want into a special vault
    function deposit() public override {
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        if (_want > 0) {
            
        }
    }

    function getName() external override pure returns (string memory) {
        return "StrategyBadgerLpMetaFarm";
    }

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
    }

    function harvest() external override{

    }


    /// @notice Withdraw partial funds, normally used with a vault withdrawal
    /// @notice A portion according to withdrawalFee goes to the rewards  
    function withdraw(uint256 _amount) external override {
        _onlyController();
        emit Withdraw(_amount);
    }

    /// @notice Withdraw all funds, normally used when migrating strategies
    /// @notice Does not trigger a withdrawal fee
    function withdrawAll() external override returns (uint256 balance) {
        _onlyController();

        balance = IERC20Upgradeable(want).balanceOf(address(this));
        emit WithdrawAll(balance);
    }


    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        // ICurveGauge(gauge).withdraw(_amount);
        return _amount;
    }
    
    function balanceOfPool() public view returns (uint256) {
        return 0;
    }

    function balanceOf() public view override returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }
}
