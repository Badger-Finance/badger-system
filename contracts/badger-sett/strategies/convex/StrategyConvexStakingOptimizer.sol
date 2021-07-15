// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/sushi/ISushiChef.sol";
import "interfaces/uniswap/IUniswapPair.sol";
import "interfaces/sushi/IxSushi.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "interfaces/convex/IBooster.sol";
import "interfaces/convex/CrvDepositor.sol";
import "interfaces/convex/IBaseRewardsPool.sol";
import "interfaces/convex/ICvxRewardsPool.sol";

import "../BaseStrategySwapper.sol";

import "../../libraries/CurveSwapper.sol";
import "../../libraries/UniswapSwapper.sol";
import "../../libraries/TokenSwapPathRegistry.sol";

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
contract StrategyConvexStakingOptimizer is BaseStrategy, CurveSwapper, UniswapSwapper, TokenSwapPathRegistry {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;
    
    // ===== Token Registry =====
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599;
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52;
    address public constant cvx = 0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B;
    address public constant cvxCrv = 0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7;
    address public constant usdc = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address public constant threeCrv = 0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490;

    IERC20Upgradeable public constant wbtcToken = IERC20Upgradeable(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599);
    IERC20Upgradeable public constant crvToken = IERC20Upgradeable(0xD533a949740bb3306d119CC777fa900bA034cd52);
    IERC20Upgradeable public constant cvxToken = IERC20Upgradeable(0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B);
    IERC20Upgradeable public constant cvxCrvToken = IERC20Upgradeable(0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7);
    IERC20Upgradeable public constant usdcToken = IERC20Upgradeable(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);
    IERC20Upgradeable public constant threeCrvToken = IERC20Upgradeable(0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490);

    // ===== Convex Registry =====
    CrvDepositor public constant crvDepositor = CrvDepositor(0x8014595F2AB54cD7c604B00E9fb932176fDc86Ae); // Convert CRV -> cvxCRV
    IBooster public constant booster = IBooster(0xF403C135812408BFbE8713b5A23a04b3D48AAE31);
    address public constant cvxCRV_CRV_SLP = 0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007; // cvxCRV/CRV SLP
    address public constant CVX_ETH_SLP = 0x05767d9EF41dC40689678fFca0608878fb3dE906; // CVX/ETH SLP
    IBaseRewardsPool public baseRewardsPool;
    IBaseRewardsPool public constant cvxCrvRewardsPool = IBaseRewardsPool(0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e);
    ICvxRewardsPool public constant cvxRewardsPool = ICvxRewardsPool(0xCF50b810E57Ac33B91dCF525C6ddd9881B139332);
    ISushiChef public constant convexMasterChef = ISushiChef(0x5F465e9fcfFc217c5849906216581a657cd60605);
    address public constant threeCrvSwap = 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7;

    uint256 public constant cvxCRV_CRV_SLP_Pid = 0;
    uint256 public constant CVX_ETH_SLP_Pid = 1;

    uint256 public constant MAX_UINT_256 = uint256(-1);

    uint256 public pid;
    address public badgerTree;
    address public cvxHelperVault;
    address public cvxCrvHelperVault;

    /**
    The default conditions for a rewards token are:
    - Collect rewards token
    - Distribute 100% via Tree to users

    === Harvest Config ===
    - autoCompoundingBps: Sell this % of rewards for underlying asset.
    - autoCompoundingPerfFee: Of the auto compounded portion, take this % as a performance fee.
    - treeDistributionPerfFee: Of the remaining portion (everything not distributed or converted via another mehcanic is distributed via the tree), take this % as a performance fee.

    === Tend Config ===
    - tendConvertTo: On tend, convert some of this token into another asset. By default with value as address(0), skip this step.
    - tendConvertBps: Convert this portion of balance into another asset.
     */
    struct RewardTokenConfig {
        uint256 autoCompoundingBps;
        uint256 autoCompoundingPerfFee;
        uint256 treeDistributionPerfFee;
        address tendConvertTo;
        uint256 tendConvertBps;
    }

    struct CurvePoolConfig {
        address swap;
        uint256 wbtcPosition;
        uint256 numElements;
    }

    event ExtraRewardsTokenSet(
        address indexed token, 
        uint256 autoCompoundingBps,
        uint256 autoCompoundingPerfFee,
        uint256 treeDistributionPerfFee,
        address tendConvertTo,
        uint256 tendConvertBps
    );

    EnumerableSetUpgradeable.AddressSet internal extraRewards; // Tokens other than CVX and cvxCRV to process as rewards
    mapping(address => RewardTokenConfig) public rewardsTokenConfig;
    CurvePoolConfig public curvePool;

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
        uint256 cvxCrvHarvested;
        uint256 cvxHarvsted;
    }

    struct TendData {
        uint256 crvTended;
        uint256 cvxTended;
        uint256 cvxCrvTended;
    }

    struct TokenSwapData {
        address tokenIn;
        uint256 totalSold;
        uint256 wantGained;
    }

    event TendState(
        uint256 crvTended,
        uint256 cvxTended,
        uint256 cvxCrvTended
    );

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[4] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig,
        CurvePoolConfig memory _curvePool
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        badgerTree = _wantConfig[1];

        cvxHelperVault = _wantConfig[2];
        cvxCrvHelperVault = _wantConfig[3];

        pid = _pid; // Core staking pool ID

        IBooster.PoolInfo memory poolInfo = booster.poolInfo(pid);
        baseRewardsPool = IBaseRewardsPool(poolInfo.crvRewards);

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approvals: Staking Pools
        IERC20Upgradeable(want).approve(address(booster), MAX_UINT_256);
        cvxToken.approve(address(cvxRewardsPool), MAX_UINT_256);
        cvxCrvToken.approve(address(cvxCrvRewardsPool), MAX_UINT_256);

        // Approvals: CRV -> cvxCRV converter
        crvToken.approve(address(crvDepositor), MAX_UINT_256);

        curvePool = CurvePoolConfig(
            _curvePool.swap,
            _curvePool.wbtcPosition,
            _curvePool.numElements
        );

        // Set Swap Paths
        address[] memory path = new address[](3);
        path[0] = usdc;
        path[1] = weth;
        path[2] = cvxCrv;
        _setTokenSwapPath(usdc, cvxCrv, path);

        path = new address[](2);
        path[0] = crv;
        path[1] = cvxCrv;
        _setTokenSwapPath(crv, cvxCrv, path);

        path = new address[](3);
        path[0] = cvxCrv;
        path[1] = weth;
        path[2] = wbtc;
        _setTokenSwapPath(cvxCrv, wbtc, path);

        path = new address[](3);
        path[0] = cvx;
        path[1] = weth;
        path[2] = wbtc;
        _setTokenSwapPath(cvx, wbtc, path);
    }

    /// ===== Permissioned Functions =====
    function setPid(uint256 _pid) external {
        _onlyGovernance();
        pid = _pid; // LP token pool ID
    }

    function addExtraRewardsToken(address _extraToken, RewardTokenConfig memory _rewardsConfig, address[] memory _swapPathToWant) external {
        _onlyGovernance();

        require(!isProtectedToken(_extraToken)); // We can't process tokens that are part of special strategy logic as extra rewards
        require(isProtectedToken(_rewardsConfig.tendConvertTo));  // We should only convert to tokens the strategy handles natively for security reasons

        /**
        === tendConvertTo Attack Vector: Rug rewards via swap ===
            - Set a token as an extra rewards token
            - Provide liquidity on that pool (disallow swaps from non-admin to avoid others messing with it)
            - Convert it to a token on tend that can be rugged by an admin    
            - Admin steals value    
        */

        extraRewards.add(_extraToken);
        rewardsTokenConfig[_extraToken] = _rewardsConfig;

        emit ExtraRewardsTokenSet(
            _extraToken, 
            _rewardsConfig.autoCompoundingBps,
            _rewardsConfig.autoCompoundingPerfFee,
            _rewardsConfig.treeDistributionPerfFee,
            _rewardsConfig.tendConvertTo,
            _rewardsConfig.tendConvertBps
        );
    }

    function removeExtraRewardsToken(address _extraToken) external {
        _onlyGovernance();
        extraRewards.remove(_extraToken);
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

    function getProtectedTokens() public override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](4);
        protectedTokens[0] = want;
        protectedTokens[1] = crv;
        protectedTokens[2] = cvx;
        protectedTokens[3] = cvxCrv;
        return protectedTokens;
    }

    function isTendable() public override view returns (bool) {
        return true;
    }

    /// ===== Internal Core Implementations =====
    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(crv) != _asset, "crv");
        require(address(cvx) != _asset, "cvx");
        require(address(cvxCrv) != _asset, "cvxCrv");
    }

    /// @dev Deposit Badger into the staking contract
    function _deposit(uint256 _want) internal override {
        // Deposit all want in core staking pool
        booster.deposit(pid, _want, true);
    }

    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
        baseRewardsPool.withdrawAndUnwrap(balanceOfPool(), false);
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
        }

        // Confirm how much want we actually end up with
        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        uint256 _withdrawn = MathUpgradeable.min(_postWant, _amount);
        emit WithdrawState(_amount, _preWant, _postWant, _withdrawn);

        return _withdrawn;
    }

    function _tendGainsFromPositions() internal {
        // Harvest CRV, CVX, cvxCRV, 3CRV, and extra rewards tokens from staking positions
        // Note: Always claim extras
        baseRewardsPool.getReward(address(this), true);

        if (cvxCrvRewardsPool.earned(address(this)) > 0) {
            cvxCrvRewardsPool.getReward(address(this), true);
        }
        
        if (cvxRewardsPool.earned(address(this)) > 0) {
            cvxRewardsPool.getReward(true);
        }
    }

    /// @notice The more frequent the tend, the higher returns will be
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // 1. Harvest gains from positions
        _tendGainsFromPositions();
        
        // Track harvested coins, before conversion
        tendData.crvTended = crvToken.balanceOf(address(this));

        // 2. Convert CRV -> cvxCRV
        if ( tendData.crvTended > 0 ) {
            _swapExactTokensForTokens(sushiswap, crv, tendData.crvTended, getTokenSwapPath(crv, cvxCrv));
        }

        // Track harvested + converted coins
        tendData.cvxCrvTended = cvxCrvToken.balanceOf(address(this));
        tendData.cvxTended = cvxToken.balanceOf(address(this));

        // 3. Stake all cvxCRV
        if (tendData.cvxCrvTended > 0) {
            cvxCrvRewardsPool.stake(tendData.cvxCrvTended);
        }
        
        // 4. Stake all CVX
        if (tendData.cvxTended > 0) {
            cvxRewardsPool.stake(cvxToken.balanceOf(address(this)));
        }

        emit Tend(0);
        emit TendState(tendData.crvTended, tendData.cvxTended, tendData.cvxCrvTended);
        return tendData;
    }
    
    // No-op until we optimize harvesting strategy. Auto-compouding is key.
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();
        HarvestData memory harvestData;

        uint256 idleWant = IERC20Upgradeable(want).balanceOf(address(this));
        
        // TODO: Harvest details still under constructuion. It's being designed to optimize yield while still allowing on-demand access to profits for users.

        // 1. Withdraw accrued rewards from staking positions (claim unclaimed positions as well)
        cvxCrvRewardsPool.withdraw(cvxCrvRewardsPool.balanceOf(address(this)), true);
        cvxRewardsPool.withdraw(cvxRewardsPool.balanceOf(address(this)), true);

        harvestData.cvxCrvHarvested = cvxCrvToken.balanceOf(address(this));
        harvestData.cvxHarvsted = cvxToken.balanceOf(address(this));

        // 2. Convert 3CRV -> cvxCRV via USDC
        uint256 threeCrvBalance = threeCrvToken.balanceOf(address(this));
        if (threeCrvBalance > 0) {
            _remove_liquidity_one_coin(threeCrvSwap, threeCrvBalance, 1, 0);
            _swapExactTokensForTokens(sushiswap, usdc, usdcToken.balanceOf(address(this)), getTokenSwapPath(usdc, cvxCrv));
        }

        // 3. Sell 20% of accured rewards for underlying
        if (harvestData.cvxCrvHarvested > 0) {
            uint256 cvxCrvToSell = harvestData.cvxCrvHarvested.mul(2000).div(MAX_FEE);
            _swapExactTokensForTokens(sushiswap, cvxCrv, cvxCrvToSell, getTokenSwapPath(cvxCrv, wbtc));
        }

        if (harvestData.cvxHarvsted > 0) {
            uint256 cvxToSell = harvestData.cvxHarvsted.mul(2000).div(MAX_FEE);
            _swapExactTokensForTokens(sushiswap, cvx, cvxToSell, getTokenSwapPath(cvx, wbtc));
        }

        // // Process extra rewards tokens
        // {
        //     for (uint256 i = 0; i < extraRewards.length(); i=i+1) {
        //         address token = extraRewards.at(i);
        //         IERC20Upgradeable tokenContract = IERC20Upgradeable(token);
        //         uint256 tokenBalance = tokenContract.balanceOf(address(this));

        //         // Sell performance fee (as wbtc) proportion
        //         uint256 sellBps = getTokenSellBps(token);
        //         _swap_uniswap(token, sellBps, getTokenSwapPath(token, wbtc));
        //         // TODO: Distribute performance fee

        //         // Distribute remainder to users
        //         // token.transfer(tokenBalance.mul(sellBps).div(MAX_BPS));
        //     }
        // }

        // 4. Roll WBTC gained into want position
        uint256 wbtcToDeposit = wbtcToken.balanceOf(address(this));

        if (wbtcToDeposit > 0) {
            _add_liquidity_single_coin(curvePool.swap, want, wbtc, wbtcToDeposit, curvePool.wbtcPosition, curvePool.numElements, 0);
            uint256 wantGained = IERC20Upgradeable(want).balanceOf(address(this)).sub(idleWant);
            // Half of gained want (10% of rewards) are auto-compounded, half of gained want is taken as a performance fee
            IERC20Upgradeable(want).transfer(IController(controller).rewards(), wantGained.mul(5000).div(MAX_FEE));
        }

        // 5. Deposit remaining CVX / cvxCRV rewards into helper vaults and distribute
        if (harvestData.cvxCrvHarvested > 0) {
            uint256 cvxCrvToDistribute = cvxCrvToken.balanceOf(address(this));
            // uint256 performanceFee = cvxCrvToDistribute.mul(performanceFeeGovernance).div(MAX_FEE);

            // cvxCrvHelperVault.depositFor(controller.rewards(), performanceFee);

            // uint256 cvxCrvToTree = cvxCrvToken.balanceOf(address(this));
            // cvxCrvHelperVault.depositFor(badgerTree, cvxCrvToTree);
            
            cvxCrvToken.transfer(badgerTree, cvxCrvToDistribute);
        }

        if (harvestData.cvxHarvsted > 0) {
            uint256 cvxToDistribute = cvxToken.balanceOf(address(this));
            cvxToken.transfer(badgerTree, cvxToDistribute);
        }

        return harvestData;
    }
}
