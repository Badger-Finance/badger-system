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
import "interfaces/badger/IStakingRewardsSignalOnly.sol";

/*
    Strategy to compound badger rewards
    - Deposit Badger into the vault to receive more from a special rewards pool
*/
contract StrategySushiBadgerWbtc is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public geyser;
    address public badger; // BADGER Token
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    address public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token

    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract
    uint256 public constant pid = 420; // LP token pool ID

    address public badgerTree;

    event HarvestLpMetaFarm(
        uint256 badgerHarvested,
        uint256 sushiHarvested,
        uint256 sushiToStrategist,
        uint256 sushiToGovernance,
        uint256 sushiToBadgerTree,
        uint256 badgerConvertedToWbtc,
        uint256 wtbcFromConversion,
        uint256 lpGained,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 badgerHarvested;
        uint256 sushiHarvested;
        uint256 sushiToStrategist;
        uint256 sushiToGovernance;
        uint256 sushiToBadgerTree;
        uint256 badgerConvertedToWbtc;
        uint256 wtbcFromConversion;
        uint256 lpGained;
    }

    struct TendData {
        uint256 sushiTended;
    }

    event WithdrawState(
        uint256 toWithdraw,
        uint256 preWant,
        uint256 postWant,
        uint256 withdrawn
    );

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[4] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        geyser = _wantConfig[1];
        badger = _wantConfig[2];
        badgerTree = _wantConfig[3];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve Chef and xSushi (aka SushiBar) to use our sushi
        IERC20Upgradeable(want).approve(chef, uint256(-1));
        IERC20Upgradeable(sushi).approve(xsushi, uint256(-1));
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.1";
    }

    function getName() external override pure returns (string memory) {
        return "StrategySushiBadgerWbtc";
    }

    function balanceOfPool() public override view returns (uint256) {
        // Note: Our want balance is actually in the SushiChef, but it is also tracked in the geyser, which is easier to read
        return IStakingRewardsSignalOnly(geyser).balanceOf(address(this));
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](5);
        protectedTokens[0] = want;
        protectedTokens[1] = geyser;
        protectedTokens[2] = badger;
        protectedTokens[3] = sushi;
        protectedTokens[4] = xsushi;
        return protectedTokens;
    }

    function isTendable() public override view returns (bool) {
        return true;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(sushi) != _asset, "sushi");
        require(address(xsushi) != _asset, "xsushi");

        require(address(geyser) != _asset, "geyser");
        require(address(badger) != _asset, "badger");
    }

    /// @dev Deposit Badger into the staking contract
    /// @dev Track balance in the StakingRewards
    function _deposit(uint256 _want) internal override {
        // Deposit all want in sushi chef
        ISushiChef(chef).deposit(pid, _want);
        
        // "Deposit" same want into personal staking rewards via signal (note: this is a SIGNAL ONLY - the staking rewards must be locked to just this account)
        IStakingRewardsSignalOnly(geyser).stake(_want);
    }

    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
        IStakingRewardsSignalOnly(geyser).exit();
        (uint256 staked, ) = ISushiChef(chef).userInfo(pid, address(this));

        // Withdraw all want from Chef
        ISushiChef(chef).withdraw(pid, staked);

        // === Transfer extra token: Sushi ===

        // Withdraw all sushi from SushiBar
        uint256 _xsushi = IERC20Upgradeable(xsushi).balanceOf(address(this));
        IxSushi(xsushi).leave(_xsushi);
        uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));

        // Send all Sushi to controller rewards
        IERC20Upgradeable(sushi).safeTransfer(IController(controller).rewards(), _sushi);

        // === Transfer extra token: Badger ===

        // "Unstake" from badger rewards source and hrvest all badger rewards
        IStakingRewardsSignalOnly(geyser).exit();

        // Send all badger rewards to controller rewards
        uint256 _badger = IERC20Upgradeable(badger).balanceOf(address(this));
        IERC20Upgradeable(badger).safeTransfer(IController(controller).rewards(), _badger);

        // Note: All want is automatically withdrawn outside this "inner hook" in base strategy function
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {

        // Get idle want in the strategy
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        // If we lack sufficient idle want, withdraw the difference from the strategy position
        if (_preWant < _amount) {
            uint256 _toWithdraw = _amount.sub(_preWant);

            ISushiChef(chef).withdraw(pid, _toWithdraw);
            // Note: Also signal withdraw from staking rewards
            IStakingRewardsSignalOnly(geyser).withdraw(_toWithdraw);

            // Note: Withdrawl process will earn sushi, this will be deposited into SushiBar on next tend()

        }

        // Confirm how much want we actually end up with
        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        uint256 _withdrawn = MathUpgradeable.min(_postWant, _amount);

        emit WithdrawState(
            _amount,
            _preWant,
            _postWant,
            _withdrawn
        );

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

    /// @dev Harvest accumulated badger rewards and convert them to LP tokens
    /// @dev Harvest accumulated sushi and send to the controller
    /// @dev Restake the gained LP tokens in the Geyser
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeSushi = IERC20Upgradeable(sushi).balanceOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeBadger = IERC20Upgradeable(badger).balanceOf(address(this));

        // ===== Harvest All Sushi: Send to tree (after performance fees) =====

        // Note: Deposit of zero harvests rewards balance, but go ahead and deposit idle want if we have it
        ISushiChef(chef).deposit(pid, _beforeLp);

        // Unstake all sushi in SushiBar, realizing increase in Sushi
        uint256 _xsushi = IERC20Upgradeable(xsushi).balanceOf(address(this));
        IxSushi(xsushi).leave(_xsushi);

        // Track gains
        uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));
        harvestData.sushiHarvested = _sushi.sub(_beforeSushi);

        // Process performance fees
        harvestData.sushiToStrategist = _processFee(sushi, harvestData.sushiHarvested, performanceFeeStrategist, strategist);
        harvestData.sushiToGovernance = _processFee(sushi, harvestData.sushiHarvested, performanceFeeGovernance, IController(controller).rewards());

        // Transfer remainder to Tree
        harvestData.sushiToBadgerTree = IERC20Upgradeable(sushi).balanceOf(address(this));
        IERC20Upgradeable(sushi).safeTransfer(badgerTree, harvestData.sushiToBadgerTree);

        // ===== Harvest all Badger rewards: Sell to underlying (no performance fees) =====
        IStakingRewardsSignalOnly(geyser).getReward();

        uint256 _afterBadger = IERC20Upgradeable(badger).balanceOf(address(this));
        harvestData.badgerHarvested = _afterBadger.sub(_beforeBadger);

        // Swap half of badger for wBTC in liquidity pool
        if (harvestData.badgerHarvested > 0) {
            harvestData.badgerConvertedToWbtc = harvestData.badgerHarvested.div(2);
            if (harvestData.badgerConvertedToWbtc > 0) {
                address[] memory path = new address[](2);
                path[0] = badger; // Badger
                path[1] = wbtc;

                _swap_sushiswap(badger, harvestData.badgerConvertedToWbtc, path);

                // Add Badger and wBTC as liquidity if any to add
                _add_max_liquidity_sushiswap(badger, wbtc);
            }
        }

        // Deposit gained LP position into Chef & staking rewards
        uint256 _afterLp = IERC20Upgradeable(want).balanceOf(address(this));
        harvestData.lpGained = _afterLp.sub(_beforeLp);
        if (harvestData.lpGained > 0) {
            _deposit(harvestData.lpGained);
        }

        emit HarvestLpMetaFarm(
            harvestData.badgerHarvested,
            harvestData.sushiHarvested,
            harvestData.sushiToStrategist,
            harvestData.sushiToGovernance,
            harvestData.sushiToBadgerTree,
            harvestData.badgerConvertedToWbtc,
            harvestData.wtbcFromConversion,
            harvestData.lpGained,
            block.timestamp,
            block.number
        );
        emit Harvest(harvestData.lpGained, block.number);

        return harvestData;
    }
}
