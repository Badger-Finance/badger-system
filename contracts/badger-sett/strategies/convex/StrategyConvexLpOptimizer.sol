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

import "interfaces/convex/ICrvDepositor.sol";
import "interfaces/convex/IBooster.sol";

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
contract StrategyConvexLpOptimizer is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // ===== Sushi Registry =====
    IERC20Upgradeable public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    IERC20Upgradeable public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token
    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract

    // ===== Convex Registry =====
    IERC20Upgradeable public constant crv = 0xd533a949740bb3306d119cc777fa900ba034cd52; // CRV token
    IERC20Upgradeable public constant cvx = 0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b; // CVX token
    IERC20Upgradeable public constant cvxCrv = 0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7; // cvxCRV token
    ICrvDepositor public constant crvDepositor = 0x8014595F2AB54cD7c604B00E9fb932176fDc86Ae; // Convert CRV -> cvxCRV
    address public constant cvxCRV_CRV_SLP = 0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b; // cvxCRV/CRV SLP
    address public constant CVX_ETH_SLP = 0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b; // CVX/ETH SLP
    IBooster public constant booster = 0xF403C135812408BFbE8713b5A23a04b3D48AAE31; // CVX Core Staking Pool

    uint256 public constant MAX_UINT_256 = uint256(-1);

    struct ConvexRegistry {
        address coreStaking;
    }

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

    struct HarvestData {
        uint256 xSushiHarvested;
        uint256 totalxSushi;
        uint256 toStrategist;
        uint256 toGovernance;
        uint256 toBadgerTree;
    }

    struct TendData {
        uint256 sushiTended;
        uint256 crvTended;
        uint256 cvxTended;
    }

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

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve Sushi: Chef and xSushi (aka SushiBar)
        IERC20Upgradeable(want).approve(chef, MAX_UINT_256);
        sushi.approve(xsushi, MAX_UINT_256);

        // Approve CVX: LP Pool
        cvx.approve(CVX_ETH_SLP, MAX_UINT_256);

        // Approve cvxCRV + CRV: LP Pool
        crv.approve(cvxCRV_CRV_SLP, MAX_UINT_256);
        cvxCrv.approve(cvxCRV_CRV_SLP, MAX_UINT_256);

        // Approve want: Core Staking Pool
        IERC20Upgradeable(want).approve(coreStaking, MAX_UINT_256);
    }

    /// ===== Permissioned Functions =====
    function setPid(uint256 _pid) external {
        _onlyGovernance();
        pid = _pid; // LP token pool ID
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.1";
    }

    function getName() external override pure returns (string memory) {
        return "StrategySushiLpOptimizer";
    }

    function balanceOfPool() public override view returns (uint256) {
        (uint256 staked, ) = ISushiChef(chef).userInfo(pid, address(this));
        return staked;
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

    function _fetchBalances(address[] memory tokens) internal returns (uint256[] memory balances) {
        
        balances = new uint256[](tokens.length);

        for (uint256 i = 0; i < tokens.length; i++) {
            balances[i] = IERC20Upgradeable(token).balanceOf(address(this));
        }
    }


    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
        // booster.withdrawAll(pid, true);

        // // === Transfer extra token: Sushi ===
        // _withdrawSushi();
        
        // uint256 sushiBal = sushi.balanceOf(address(this));
        // uint256 xsushiBal = xSushi.balanceOf(address(this));
        // uint256 crvBal = crv.balanceOf(address(this));
        // uint256 cvxBal = cvx.balanceOf(address(this));
        // uint256 cvxCrvBal = cvxCrv.balanceOf(address(this));
        // uint256 cvxCRV_CRV_SLP_Bal = cvxCRV_CRV_SLP.balanceOf(address(this));
        // uint256 CVX_ETH_SLP_Bal = CVX_ETH_SLP.balanceOf(address(this));

        // // Send all Sushi to controller rewards
        // xSushi.safeTransfer(IController(controller).rewards(), xsushiBal);

        // Note: All want is automatically withdrawn outside this "inner hook" in base strategy function
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // Get idle want in the strategy
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        // If we lack sufficient idle want, withdraw the difference from the strategy position
        if (_preWant < _amount) {
            uint256 _toWithdraw = _amount.sub(_preWant);
            booster.withdraw(pid, _toWithdraw);
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
        // Harvest Sushi
        ISushiChef(chef).deposit(pid, 0);

        // Harvest CRV + CVX
        // coreStaking.getRewards();
    }

    function _tendSushi(uint256 sushiToDeposit) internal {
        if (sushiToDeposit > 0) {
            IxSushi(xsushi).enter(sushiToDeposit);
        }
    }

    function _tend_CRV_cvxCRV_SLP(uint256 crvToDeposit) internal {
        // 1. Convert half CRV -> cvxCRV
        uint256 halfCrv = crvToDeposit.div(2);
        crvDepositor.deposit(halfCrv, false, address(0)); // Note: Do not stake, we will use for LP instead
        // Security Note: What if there is other crvCVX sitting around in the strategy from outside sources?
        // Excess coins will accumulate and possibly be deposited on future tends

        // 2. LP on Sushi
        _add_max_liquidity_sushiswap(crv, cvxCrv);

        //TODO: Sanity checks and limits
    }

    function _tend_CVX_ETH_SLP(uint256 cvxToDeposit) internal {
        // 1. Swap Half CVX -> ETH
        uint256 halfCvx = cvxToDeposit.div(2);
        _swapEthOut_sushiswap(cvx, halfCvx, [cvx, weth]);

        _add_max_liquidity_eth_sushiswap(cvx);

        //TODO: Sanity checks and limits
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
        tendData.sushiTended = sushi.balanceOf(address(this));
        tendData.crvTended = crv.balanceOf(address(this));
        tendData.cvxTended = cvx.balanceOf(address(this));

        // Stage 2: Convert & deposit gains into positions
        _tendSushi(tendData.sushiTended);
        _tend_CRV_cvxCRV_SLP(tendData.crvTended);
        _tend_CVX_ETH_SLP(tendData.cvxTended);

        emit Tend(tendData.sushiTended);
        return tendData;
    }
    
    // No-op until we optimize harvesting strategy. Auto-compouding is key.
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();
        HarvestData memory harvestData;
        return harvestData;
    }
}
