// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/digg/IDigg.sol";

import "interfaces/sushi/ISushiChef.sol";
import "interfaces/sushi/IxSushi.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/uniswap/IUniswapV2Pair.sol";

import "../BaseStrategySwapper.sol";
import "interfaces/uniswap/IStakingRewards.sol";

/*
    Strategy to compound DIGG LP Position
    - Harvest DIGG from special rewards pool and sell to increase LP Position
    - Optimize Sushi gains from onsen rewards, if present
    - Sushi rewards will be distrtibuted via the BadgerTree in the form of interest-bearing xSushi
*/
contract StrategySushiDiggWbtcLpOptimizer is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public diggFaucet;
    address public digg; // DIGG Token
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    address public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token

    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract
    uint256 public pid; // LP token pool id

    address public badgerTree;

    event HarvestState(
        uint256 xSushiHarvested,
        uint256 totalxSushi,
        uint256 toStrategist,
        uint256 toGovernance,
        uint256 toBadgerTree,
        uint256 timestamp,
        uint256 blockNumber
    );

    event HarvestDiggState(
        uint256 diggHarvested,
        uint256 diggConvertedToWbtc,
        uint256 wbtcFromConversion,
        uint256 lpGained,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 diggHarvested;
        uint256 xSushiHarvested;
        uint256 totalxSushi;
        uint256 toStrategist;
        uint256 toGovernance;
        uint256 toBadgerTree;
        uint256 diggConvertedToWbtc;
        uint256 wbtcFromConversion;
        uint256 lpGained;
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
        address[4] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        diggFaucet = _wantConfig[1];
        digg = _wantConfig[2];
        badgerTree = _wantConfig[3];

        pid = _pid; // LP token pool ID

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve Chef and xSushi (aka SushiBar) to use our sushi
        require(IERC20Upgradeable(want).approve(chef, uint256(-1)));
        require(IERC20Upgradeable(sushi).approve(xsushi, uint256(-1)));
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.1";
    }

    function getName() external override pure returns (string memory) {
        return "StrategySushiDiggWbtcLpOptimizer";
    }

    function balanceOfPool() public override view returns (uint256) {
        // Note: Our want balance is actually in the SushiChef.
        (uint256 staked, ) = ISushiChef(chef).userInfo(pid, address(this));
        return staked;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](5);
        protectedTokens[0] = want;
        protectedTokens[1] = diggFaucet;
        protectedTokens[2] = digg;
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

        require(address(diggFaucet) != _asset, "diggFaucet");
        require(address(digg) != _asset, "digg");
    }

    /// @dev Deposit DIGG into the sushi chef.
    function _deposit(uint256 _want) internal override {
        ISushiChef(chef).deposit(pid, _want);
    }

    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
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

        // === Transfer extra token: DIGG ===

        // Harvest all pending digg rewards
        IStakingRewards(diggFaucet).getReward();

        // Send all digg rewards to controller rewards
        uint256 _diggBalance = IDigg(digg).balanceOf(address(this));
        IDigg(digg).transfer(IController(controller).rewards(), _diggBalance);

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
            // Note: Withdrawl process will earn sushi, this will be deposited into SushiBar on next tend()
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

    /// @dev Harvest accumulated digg rewards and convert them to LP tokens
    /// @dev Harvest accumulated sushi and send to the controller
    /// @dev Restake the gained LP tokens in the diggFaucet
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforexSushi = IERC20Upgradeable(xsushi).balanceOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeDigg = IERC20Upgradeable(digg).balanceOf(address(this));

        // ===== Harvest sushi rewards from Chef =====

        // Note: Deposit of zero harvests rewards balance, but go ahead and deposit idle want if we have it
        ISushiChef(chef).deposit(pid, _beforeLp);

        // Put all sushi into xsushi
        uint256 _sushi = IERC20Upgradeable(sushi).balanceOf(address(this));

        if (_sushi > 0) {
            IxSushi(xsushi).enter(_sushi);
        }

        uint256 _xsushi = IERC20Upgradeable(xsushi).balanceOf(address(this));

        //all xsushi is profit
        harvestData.totalxSushi = _xsushi;
        //harvested is the xsushi gain since last tend
        harvestData.xSushiHarvested = _xsushi.sub(_beforexSushi);

        // Process performance fees
        //performance fees in xsushi
        harvestData.toStrategist = _processFee(xsushi, harvestData.totalxSushi, performanceFeeStrategist, strategist);
        harvestData.toGovernance = _processFee(xsushi, harvestData.totalxSushi, performanceFeeGovernance, IController(controller).rewards());

        // Transfer remainder to Tree
        //tree gets xsushi instead of sushi so it keeps compounding
        harvestData.toBadgerTree = IERC20Upgradeable(xsushi).balanceOf(address(this));
        IERC20Upgradeable(xsushi).safeTransfer(badgerTree, harvestData.toBadgerTree);

        // ===== Harvest all DIGG rewards: Sell to underlying (no performance fees) =====

        IStakingRewards(diggFaucet).getReward();

        uint256 _afterDigg = IERC20Upgradeable(digg).balanceOf(address(this));
        harvestData.diggHarvested = _afterDigg.sub(_beforeDigg);

        // ===== Swap half of digg for wBTC in liquidity pool =====
        if (harvestData.diggHarvested > 0) {
            harvestData.diggConvertedToWbtc = harvestData.diggHarvested.div(2);
            if (harvestData.diggConvertedToWbtc > 0) {
                address[] memory path = new address[](2);
                path[0] = digg; // Digg
                path[1] = wbtc;

                // Note: We must sync before trading due to having a rebasing asset in the pair
                address pair = _get_sushi_pair(digg, wbtc);
                IUniswapV2Pair(pair).sync();

                _swap_sushiswap(digg, harvestData.diggConvertedToWbtc, path);
                               
                harvestData.wbtcFromConversion = IERC20Upgradeable(wbtc).balanceOf(address(this));

                // Add DIGG and wBTC as liquidity if any to add
                _add_max_liquidity_sushiswap(digg, wbtc);
            }
        }

        // ===== Deposit gained LP position into Chef & staking rewards =====
        uint256 _afterLp = IERC20Upgradeable(want).balanceOf(address(this));
        harvestData.lpGained = _afterLp.sub(_beforeLp);

        if (harvestData.lpGained > 0) {
            _deposit(harvestData.lpGained);
        }

        emit HarvestState(
            harvestData.xSushiHarvested,
            harvestData.totalxSushi,
            harvestData.toStrategist,
            harvestData.toGovernance,
            harvestData.toBadgerTree,
            block.timestamp,
            block.number
        );

        emit HarvestDiggState(
            harvestData.diggHarvested,
            harvestData.diggConvertedToWbtc,
            harvestData.wbtcFromConversion,
            harvestData.lpGained,
            block.timestamp,
            block.number
        );

        emit Harvest(harvestData.lpGained, block.number);

        return harvestData;
    }
}
