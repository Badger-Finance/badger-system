// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapPair.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/pickle/IPickleJar.sol";
import "interfaces/pickle/IPickleChef.sol";
import "interfaces/pickle/IPickleStaking.sol";

import "../BaseStrategy.sol";

contract StrategyPickleMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public pickleJar;
    uint256 public pid; // Pickle Chef Token ID

    address public constant pickle = 0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5;
    address public constant pickleChef = 0xbD17B1ce622d73bD438b9E658acA5996dc394b0d;
    address public constant uniswap = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address public constant pickleStaking = 0xa17a8883dA1aBd57c690DF9Ebf58fC194eDAb66F;
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route

    address public pairToken0;
    address public pairToken1;

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _want,
        address _pickleJar,
        uint256 _pid,
        uint256[3] memory _feeConfig
    ) public initializer {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;

        want = _want;
        pickleJar = _pickleJar;
        pid = _pid;

        // (address lp, , , ) = IPickleChef(pickleChef).poolInfo(pid);

        // // Confirm pickle-related addresses
        // require(IPickleJar(pickleJar).token() == address(want), "PickleJar & Want mismatch");
        // require(lp == pickleJar, "pid & Pickle jar mismatch");

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // // Get the underlying assets of want
        // pairToken0 = IUniswapPair(address(want)).token0();
        // pairToken1 = IUniswapPair(address(want)).token1();

        // // Trust Uniswap with unlimited approval for swapping efficiency
        // IERC20Upgradeable(pickle).safeApprove(uniswap, type(uint256).max);
        // IERC20Upgradeable(pairToken0).safeApprove(uniswap, type(uint256).max);
        // IERC20Upgradeable(pairToken1).safeApprove(uniswap, type(uint256).max);
    }

    function getName() external override pure returns (string memory) {
        return "StrategyPickleMetaFarm";
    }

    /// @notice Deposit any want in the strategy into the mechanics
    /// @dev want -> pickleJar, pWant -> pWantFarm
    function deposit() public override {}

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(want != _asset, "want");
        require(pickleJar != _asset, "pickleJar");
        require(pickle != _asset, "pickle");
    }

    /// @notice Withdraw partial funds, normally used with a vault withdrawal
    function withdraw(uint256 _amount) external override {
        _onlyController();
    }

    /// @notice Withdraw all funds and transfer them to the vault, without charging any withdrawal fees. Intended to be used when migrating strategies.
    function withdrawAll() external override returns (uint256 balance) {
        _onlyController();
        return 0;
    }

    /// @dev Harvest farmed pickle for pToken farm & pickle farm (if applicable), redeposit into pickle farm.
    function harvest() external override {
        _onlyGovernanceOrStrategist();

        // Can we harvest from pickle staking?
        // Can we harvest from pToken farm?

        // If we have pickle now, redeposit it into pickle farm
    }

    function _swap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        IERC20Upgradeable(startToken).safeApprove(uniswap, 0);
        IERC20Upgradeable(startToken).safeApprove(uniswap, balance);
        IUniswapRouterV2(uniswap).swapExactTokensForTokens(balance, uint256(0), path, address(this), now.add(1800));
    }

    /// @notice Partially withdraw from strategy, unrolling rewards
    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        // Harvest & withdraw from metafarm

        // Harvest & withdraw from pickle farm

        // Withdraw from pickle vault
        // Convert pickle into underlying
        return _amount;
    }

    function balanceOfPool() public view returns (uint256) {
        return 0;
    }

    function balanceOf() public override view returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }
}
