// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/sushi/ISushiChef.sol";
import "interfaces/sushi/IxSushi.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../BaseStrategySwapper.sol";

/*
    Optimize Sushi rewards for arbitrary Sushi LP pair
*/
contract StrategySushiLpOptimizer is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    address public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token

    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract
    uint256 public pid;

    address public badgerTree;

    event HarvestState(uint256 sushiHarvested, uint256 totalSushi, uint256 toStrategist, uint256 toGovernance, uint256 toBadgerTree, uint256 timestamp, uint256 blockNumber);

    struct HarvestData {
        uint256 sushiHarvested;
        uint256 totalSushi;
        uint256 toStrategist;
        uint256 toGovernance;
        uint256 toBadgerTree;
    }

    struct TendData {
        uint256 sushiTended;
    }

    event WithdrawState(uint256 toWithdraw, uint256 preWant, uint256 postWant, uint256 withdrawn);

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[2] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        badgerTree = _wantConfig[1];
        pid = _pid; // LP token pool ID

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve xsushi (aka SushiBar) to use our sushi
        IERC20Upgradeable(want).approve(chef, uint256(-1));
        IERC20Upgradeable(sushi).approve(xsushi, uint256(-1));
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.1";
    }

    function getName() external pure override returns (string memory) {
        return "StrategySushiLpOptimizer";
    }

    function balanceOfPool() public view override returns (uint256) {
        (uint256 staked, ) = ISushiChef(chef).userInfo(pid, address(this));
        return staked;
    }

    function getProtectedTokens() external view override returns (address[] memory) {
        address[] memory protectedTokens = new address[](5);
        protectedTokens[0] = want;
        protectedTokens[1] = sushi;
        protectedTokens[2] = xsushi;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(sushi) != _asset, "sushi");
        require(address(xsushi) != _asset, "xsushi");
    }

    /// @dev Deposit Badger into the staking contract
    /// @dev Track balance in the StakingRewards
    function _deposit(uint256 _want) internal override {
        // Deposit all want in sushi chef
        ISushiChef(chef).deposit(pid, _want);
    }

    /// @dev Exit all positions and send any gained tokens to controller rewards
    function _withdrawAll() internal override {
        (uint256 staked, ) = ISushiChef(chef).userInfo(pid, address(this));

        // Withdraw all from Chef
        ISushiChef(chef).withdraw(pid, staked);

        // Withdraw all sushi from SushiBar
        uint256 _xsushi = IERC20Upgradeable(xsushi).balanceOf(address(this));
        IxSushi(xsushi).leave(_xsushi);

        uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));

        // Send all Sushi to controller rewards
        IERC20Upgradeable(sushi).safeTransfer(IController(controller).rewards(), _sushi);
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // Get idle want in the strategy
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        // If we lack sufficient idle want, withdraw the difference from the strategy position
        if (_preWant < _amount) {
            uint256 _toWithdraw = _amount.sub(_preWant);
            ISushiChef(chef).withdraw(pid, _toWithdraw);

            // If we harvested any sushi in withdrawal process, stake it
            uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));
            IxSushi(xsushi).enter(_sushi);
        }

        // Confirm how much want we actually end up with
        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        uint256 _withdrawn = MathUpgradeable.min(_postWant, _amount);

        emit WithdrawState(_amount, _preWant, _postWant, _withdrawn);

        return _withdrawn;
    }

    /// @notice Harvest sushi gains from Chef and deposit into SushiBar (xSushi) to increase gains
    /// @notice Any excess Sushi sitting in the Strategy will be staked as well
    /// @notice The more frequent the tend, the higher returns will be
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // Note: Deposit of zero harvests rewards balance.
        ISushiChef(chef).deposit(pid, 0);

        tendData.sushiTended = IERC20Upgradeable(sushi).balanceOf(address(this));

        // Stake any harvested sushi in SushiBar to increase returns
        if (tendData.sushiTended > 0) {
            IxSushi(xsushi).enter(tendData.sushiTended);
        }

        emit Tend(tendData.sushiTended);
        return tendData;
    }

    /// @dev Harvest accumulated sushi from SushiChef and SushiBar and send to rewards tree for distribution. Take performance fees on gains
    /// @dev The less frequent the harvest, the higher the gains due to compounding
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeSushi = IERC20Upgradeable(sushi).balanceOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));

        // == Harvest sushi rewards from Chef ==
        // Note: Deposit of zero harvests rewards balance, but go ahead and deposit idle want if we have it
        ISushiChef(chef).deposit(pid, _beforeLp);

        // == Unstake all sushi in SushiBar, realizing increase in Sushi ==
        uint256 _xsushi = IERC20Upgradeable(xsushi).balanceOf(address(this));
        IxSushi(xsushi).leave(_xsushi);

        // Track gains
        uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));
        harvestData.totalSushi = _sushi;
        harvestData.sushiHarvested = _sushi.sub(_beforeSushi);

        // Process performance fees
        harvestData.toStrategist = _processFee(sushi, harvestData.sushiHarvested, performanceFeeStrategist, strategist);
        harvestData.toGovernance = _processFee(sushi, harvestData.sushiHarvested, performanceFeeGovernance, IController(controller).rewards());

        // Transfer remainder to Tree
        harvestData.toBadgerTree = IERC20Upgradeable(sushi).balanceOf(address(this));
        IERC20Upgradeable(sushi).safeTransfer(badgerTree, harvestData.toBadgerTree);

        emit HarvestState(
            harvestData.sushiHarvested, 
            harvestData.totalSushi, 
            harvestData.toStrategist,
            harvestData.toGovernance,
            harvestData.toBadgerTree,
            block.timestamp,
            block.number);

        // We never increase underlying position
        emit Harvest(0, block.number);

        return harvestData;
    }
}
