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
import "interfaces/uniswap/IUniswapPair.sol";
import "interfaces/sushi/IxSushi.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "interfaces/curve/ICurveGauge.sol";

import "interfaces/convex/IBooster.sol";
import "interfaces/convex/CrvDepositor.sol";
import "interfaces/convex/IClaimZap.sol";
import "interfaces/convex/IBaseRewardsPool.sol";
import "interfaces/convex/ICvxRewardsPool.sol";

import "../BaseStrategySwapper.sol";

/*
    === Deposit ===
    Deposit & Stake underlying asset into appropriate convex vault (deposit + stake is atomic)

    === Tend ===

    == Stage 1: Realize gains from all positions ==
    Harvest CRV and CVX from core vault rewards pool
    Harvest CVX and SUSHI from CVX/ETH LP
    Harvest CVX and SUSHI from cvxCRV/CRV LP

    Harvested coins:
    CRV
    CVX
    SUSHI

    == Stage 2: Deposit all gains into staked positions ==
    Zap all CRV -> cvxCRV/CRV
    Zap all CVX -> CVX/ETH
    Stake Sushi

    Position coins:
    cvxCRV/CRV
    CVX/ETH
    xSushi

    These position coins will be distributed on harvest

*/
contract StrategyConvexStakingOptimizer is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;
    
    // ===== Token Registry =====
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // WETH token
    address public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant cvx = 0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B; // CVX token
    address public constant cvxCrv = 0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7; // cvxCRV token

    IERC20Upgradeable public constant crvToken = IERC20Upgradeable(0xD533a949740bb3306d119CC777fa900bA034cd52); // CRV token
    IERC20Upgradeable public constant cvxToken = IERC20Upgradeable(0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B); // CVX token
    IERC20Upgradeable public constant cvxCrvToken = IERC20Upgradeable(0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7); // cvxCRV token
    IERC20Upgradeable public constant sushiToken = IERC20Upgradeable(0x6B3595068778DD592e39A122f4f5a5cF09C90fE2); // SUSHI token
    IERC20Upgradeable public constant xsushiToken = IERC20Upgradeable(0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272); // xSUSHI token

    // ===== Sushi Registry =====
    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract

    // ===== Convex Registry =====
    CrvDepositor public constant crvDepositor = CrvDepositor(0x8014595F2AB54cD7c604B00E9fb932176fDc86Ae); // Convert CRV -> cvxCRV
    address public constant cvxCRV_CRV_SLP = 0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007; // cvxCRV/CRV SLP
    address public constant CVX_ETH_SLP = 0x05767d9EF41dC40689678fFca0608878fb3dE906; // CVX/ETH SLP
    IBooster public constant booster = IBooster(0xF403C135812408BFbE8713b5A23a04b3D48AAE31);
    IBaseRewardsPool public baseRewardsPool;
    IBaseRewardsPool public constant cvxCrvRewardsPool = IBaseRewardsPool(0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e);
    ICrvRewardsPool public constant cvxRewardPool = ICrvRewardsPool(0xCF50b810E57Ac33B91dCF525C6ddd9881B139332);
    ISushiChef public constant convexMasterChef = ISushiChef(0x5F465e9fcfFc217c5849906216581a657cd60605);
    IClaimZap public constant claimZap = IClaimZap(0xAb9F4BB0aDD2CFbb168da95C590205419cD71f9B);

    IERC20Upgradeable public constant cvxCRV_CRV_SLP_Token = IERC20Upgradeable(0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007); // cvxCRV/CRV SLP
    IERC20Upgradeable public constant CVX_ETH_SLP_Token = IERC20Upgradeable(0x05767d9EF41dC40689678fFca0608878fb3dE906); // CVX/ETH SLP

    uint256 public constant cvxCRV_CRV_SLP_Pid = 0;
    uint256 public constant CVX_ETH_SLP_Pid = 1;

    uint256 public constant MAX_UINT_256 = uint256(-1);

    uint256 public pid;
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

    event WithdrawState(uint256 toWithdraw, uint256 preWant, uint256 postWant, uint256 withdrawn);

    struct HarvestData {
        uint256 xSushiHarvested;
        uint256 totalxSushi;
        uint256 toStrategist;
        uint256 toGovernance;
        uint256 toBadgerTree;
    }

    struct TendData {
        uint256 crvTended,
        uint256 cvxTended,
        uint256 cvxCrvTended,
    }

    event TendState(
        uint256 crvTended,
        uint256 cvxTended,
        uint256 cvxCrvTended,
    );

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

        pid = _pid; // Core staking pool ID

        IBooster.PoolInfo memory poolInfo = booster.poolInfo(pid);
        baseRewardsPool = IBaseRewardsPool(poolInfo.crvRewards);

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve Sushi: Chef and xSushi (aka SushiBar)
        IERC20Upgradeable(want).approve(chef, MAX_UINT_256);
        sushiToken.approve(xsushi, MAX_UINT_256);

        // Approve CVX + cvxCRV + CRV: Sushi Router
        // (This is handled automatically on each swap)

        // Approve want: Core Staking Pool
        IERC20Upgradeable(want).approve(address(booster), MAX_UINT_256);

        crvToken.approve(address(crvDepositor), MAX_UINT_256);
        cvxCrvToken.approve(address(cvxCrvRewardsPool), MAX_UINT_256);
    }

    /// ===== Permissioned Functions =====
    function setPid(uint256 _pid) external {
        _onlyGovernance();
        pid = _pid; // LP token pool ID
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.0";
    }

    function getName() external override pure returns (string memory) {
        return "StrategyConvexStakingOptimizer";
    }

    function balanceOfPool() public override view returns (uint256) {
        return baseRewardsPool.balanceOf(address(this));
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](5);
        protectedTokens[0] = want;
        protectedTokens[1] = sushi;
        protectedTokens[2] = xsushi;
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
    }

    /// @dev Deposit Badger into the staking contract
    function _deposit(uint256 _want) internal override {
        // Deposit all want in core staking pool
        booster.deposit(pid, _want, true);
    }

    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
        // TODO: Functionality not required for initial migration
        // Note: All want is automatically withdrawn outside this "inner hook" in base strategy function
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // Get idle want in the strategy
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        // If we lack sufficient idle want, withdraw the difference from the strategy position
        if (_preWant < _amount) {
            uint256 _toWithdraw = _amount.sub(_preWant);
            baseRewardsPool.withdrawAndUnwrap(_toWithdraw, false);
            // Note: Withdrawl process will earn sushi, this will be deposited into SushiBar on next tend()
        }

        // Confirm how much want we actually end up with
        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        uint256 _withdrawn = MathUpgradeable.min(_postWant, _amount);
        emit WithdrawState(_amount, _preWant, _postWant, _withdrawn);

        return _withdrawn;
    }

    function _tendGainsFromPositions() internal {
        // Harvest CRV, CVX, cvxCRV, 3CRV from staking positions
        baseRewardsPool.getReward(address(this), true);
        cvxCrvRewardsPool.getReward(address(this), true);
        cvxRewardsPool.getReward(true);
    }

    function _convert_CRV_to_cvxCRV(uint256 crvToDeposit) internal {
        // 1. Convert CRV -> cvxCRV
        // Selling should recieve better price always
        address[] memory path = new address[](2);
        path[0] = crv;
        path[1] = cvxCrv;

        _swapEthOut_sushiswap(crv, crvToDeposit, path);
    }
    
    /// @notice Harvest sushi gains from Chef and deposit into SushiBar (xSushi) to increase gains
    /// @notice Any excess Sushi sitting in the Strategy will be staked as well
    /// @notice The more frequent the tend, the higher returns will be
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // Stage 1: Harvest gains from positions
        _tendGainsFromPositions();
        
        // Track harvested coins
        tendData.crvTended = crvToken.balanceOf(address(this));
        tendData.cvxTended = cvxToken.balanceOf(address(this));
        
        // Stage 2: Convert & deposit gains into positions

        // 1. Convert CRV -> cvxCRV
        if ( tendData.crvTended > 0 ) {
            _convert_CRV_to_cvxCRV(tendData.crvTended);
        }

        // Get cvxCRV balance after all conversions
        tendData.cvxCrvTended = cvxCrvToken.balanceOf(address(this));

        // 3. Stake cvxCRV
        if (tendData.cvxCrvTended > 0) {
            cvxCrvRewardsPool.stake(tendData.cvxCrvTended);
        }

        // 3. Stake CVX
        if (tendData.cvxTended > 0 ) {
            cvxRewardPool.stake(tendData.cvxTended);
        }

        emit Tend(0);
        emit TendState(tendData.crvTended, tendData.cvxTended, tendData.cvxCrvTended);
        return tendData;
    }
    
    // No-op until we optimize harvesting strategy. Auto-compouding is key.
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();
        HarvestData memory harvestData;
        // TODO: Harvest details still under constructuion. It's being designed to optimize yield while still allowing on-demand access to profits for users.
        return harvestData;
    }
    receive() external payable {}
}
