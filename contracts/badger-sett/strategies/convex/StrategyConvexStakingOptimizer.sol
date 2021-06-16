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
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;
    
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
    ICvxRewardsPool public constant cvxRewardsPool = ICvxRewardsPool(0xCF50b810E57Ac33B91dCF525C6ddd9881B139332);
    ISushiChef public constant convexMasterChef = ISushiChef(0x5F465e9fcfFc217c5849906216581a657cd60605);
    IClaimZap public constant claimZap = IClaimZap(0xAb9F4BB0aDD2CFbb168da95C590205419cD71f9B);

    IERC20Upgradeable public constant cvxCRV_CRV_SLP_Token = IERC20Upgradeable(0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007); // cvxCRV/CRV SLP
    IERC20Upgradeable public constant CVX_ETH_SLP_Token = IERC20Upgradeable(0x05767d9EF41dC40689678fFca0608878fb3dE906); // CVX/ETH SLP

    uint256 public constant cvxCRV_CRV_SLP_Pid = 0;
    uint256 public constant CVX_ETH_SLP_Pid = 1;

    uint256 public constant MAX_UINT_256 = uint256(-1);

    uint256 public pid;
    address public badgerTree;

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

    event ExtraRewardsTokenSet(
        address indexed token, 
        uint256 autoCompoundingBps,
        uint256 autoCompoundingPerfFee,
        uint256 treeDistributionPerfFee,
        address tendConvertTo,
        uint256 tendConvertBps
    );

    mapping(address => mapping(address => address[])) public tokenSwapPaths;
    EnumerableSetUpgradeable.AddressSet internal extraRewards; // Tokens other than CVX and cvxCRV to process as rewards
    mapping(address => RewardTokenConfig) public rewardsTokenConfig;

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

    

    event TokenSwapPathSet(address tokenIn, address tokenOut, address[] path);

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

        // Approvals: Staking Pools
        IERC20Upgradeable(want).approve(address(booster), MAX_UINT_256);
        cvxToken.approve(address(cvxRewardsPool), MAX_UINT_256);
        cvxCrvToken.approve(address(cvxCrvRewardsPool), MAX_UINT_256);

        // Approvals: CRV -> cvxCRV converter
        crvToken.approve(address(crvDepositor), MAX_UINT_256);
    }

    /// ===== Permissioned Functions =====
    function setPid(uint256 _pid) external {
        _onlyGovernance();
        pid = _pid; // LP token pool ID
    }

    function getTokenSwapPath(address tokenIn, address tokenOut) public view returns (address[] memory) {
        return tokenSwapPaths[tokenIn][tokenOut];
    }

    /// ===== Permissioned Functions: Governance / Strategist =====
    function setTokenSwapPath(
        address tokenIn,
        address tokenOut,
        address[] calldata path
    ) external {
        _onlyGovernanceOrStrategist();
        tokenSwapPaths[tokenIn][tokenOut] = path;
        emit TokenSwapPathSet(tokenIn, tokenOut, path);
    }
    function addExtraRewardsToken(address _extraToken, RewardTokenConfig memory _rewardsConfig) external {
        _onlyGovernanceOrStrategist();

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
        _onlyGovernanceOrStrategist();
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

    function isProtectedToken(address token) public view returns (bool) {
        address[] memory protectedTokens = getProtectedTokens();
        for (uint256 i = 0; i < protectedTokens.length; i++) {
            if (token == protectedTokens[i]) {
                return true;
            }
        }
        return false;
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

    function _convert_CRV_to_cvxCRV(uint256 crvToDeposit) internal {
        // 1. Convert CRV -> cvxCRV
        // Selling should recieve better price always
        address[] memory path = new address[](2);
        path[0] = crv;
        path[1] = cvxCrv;

        _swap_sushiswap(crv, crvToDeposit, path);
    }

    /// @notice The more frequent the tend, the higher returns will be
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // Stage 1: Harvest gains from positions
        _tendGainsFromPositions();
        
        // Stage 2: Convert & deposit gains into positions

        
        // 2. Process Extra Rewards Tokens
        // for (uint256 i=0; i < extraRewards.length(); i++) {
        //     address token = extraRewards.at(i);
        //     if (rewardsTokenConfig[token].tendConvertTo != address(0) {
        //         uint256 tokenBal = IERC20Upgradeable(token).balanceOf(address(this));
        //         _swap(token, tokenBal, getTokenSwapPath(token, tendConvertTo));
        //     }
        // }

        // Track harvested + converted coins
        tendData.cvxCrvTended = cvxCrvToken.balanceOf(address(this));
        tendData.crvTended = crvToken.balanceOf(address(this));
        tendData.cvxTended = cvxToken.balanceOf(address(this));

        // 1. Convert CRV -> cvxCRV
        if ( tendData.crvTended > 0 ) {
            _convert_CRV_to_cvxCRV(tendData.crvTended);
        }

        // 3. Stake all cvxCRV
        if (tendData.cvxCrvTended > 0) {
            cvxCrvRewardsPool.stake(tendData.cvxCrvTended);
        }
        
        require(cvxToken.balanceOf(address(this)) == tendData.cvxTended, "cvx-balance-mismatch");

        // 4. Stake all CVX
        if (tendData.cvxTended > 0) {
            cvxToken.approve(address(cvxRewardsPool), MAX_UINT_256);
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
        // require(false, "Harvest functionality under development");

        // uint256 idleWant = IERC20Upgradeable(want).balanceOf(address(this));
        
        // // TODO: Harvest details still under constructuion. It's being designed to optimize yield while still allowing on-demand access to profits for users.

        // // Withdraw accrued rewards from staking positions (claim unclaimed positions as well)
        // cvxCrvRewardsPool.withdraw(cvxCrvRewardsPool.balanceOf(address(this)), true);
        // cvxRewardsPool.withdraw(cvxRewardsPool.balanceOf(address(this)), true);

        // harvestData.cvxCrvHarvested = cvxCrvToken.balanceOf(address(this));
        // harvestData.cvxHarvsted = cvxToken.balanceOf(address(this));

        // uint256 cvxCrvToSell = harvestData.cvxCrvHarvested.mul(2000).div(MAX_FEE);
        // uint256 cvxToSell = harvestData.cvxHarvsted.mul(2000).div(MAX_FEE);

        // // Sell 20% of accured rewards for underlying
        // _swap_uniswap(cvxCrv, cvxCrvToSell, getTokenSwapPath(cvxCrv, wbtc));
        // _swap_uniswap(cvx, cvxToSell, getTokenSwapPath(cvx, wbtc));

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

        // // TODO: LP into curve position

        // uint256 wantGained = IERC20Upgradeable(want).balanceOf(address(this)).sub(idleWant);

        // // Half of gained want (10% of rewards) are auto-compounded, half of gained want is taken as a performance fee
        // IERC20Upgradeable(want).transfer(IController(controller).rewards(), wantGained.mul(5000).div(MAX_FEE));

        // // Distribute 60% of accrued rewards as vault positions via tree
        // uint256 cvxCrvToDistribute = harvestData.cvxCrvHarvested.mul(6000).div(MAX_FEE);
        // uint256 cvxToDistribute = harvestData.cvxHarvsted.mul(6000).div(MAX_FEE);

        // cvxCrvToken.transfer(badgerTree, cvxCrvToDistribute);
        // cvxToken.transfer(badgerTree, cvxToDistribute);

        // // Take 20% performance fee rewards assets
        // uint256 cvxCrvPerformanceFee = cvxCrvToken.balanceOf(address(this));
        // uint256 cvxPerformanceFee = cvxToken.balanceOf(address(this));

        // cvxCrvToken.transfer(IController(controller).rewards(), cvxCrvPerformanceFee);
        // cvxToken.transfer(IController(controller).rewards(), cvxPerformanceFee);

        return harvestData;
    }

    /// @dev Path must be set to sell token for want
    function _swapTokenForWant(address tokenIn, uint256 amount) internal {
        _swap_uniswap(tokenIn, amount, getTokenSwapPath(tokenIn, want));
    }

    receive() external payable {}
}
