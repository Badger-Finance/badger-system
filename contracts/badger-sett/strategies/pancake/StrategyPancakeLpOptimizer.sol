// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/pancake/IPancakeStaking.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../PancakeSwapper.sol";
import "interfaces/badger/IStakingRewardsSignalOnly.sol";

/*
    ===== Pancake LP Optimizer =====
    - Stake LP tokens for Cake rewards, sell these evenly for underlying assets & LP
    - Performance fees are taken on Cake directly
    - Swap half of cake for each LP asset:
        token0 = x, path = [x, y, z]
        token1 = x, path = [x, y, z]

    These can be parameters on construction
*/
contract StrategyPancakeLpOptimizer is PancakeSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    IPancakeStaking public constant chef = IPancakeStaking(0x73feaa1eE314F8c655E354234017bE2193C9E24E); // Master staking contract
    IERC20Upgradeable public constant cake = IERC20Upgradeable(0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82); // Cake Token
    IERC20Upgradeable public constant syrup = IERC20Upgradeable(0x009cF7bC57584b7998236eff51b98A168DceA9B0); // Syrup Token

    uint256 public constant cakePid = 0;
    uint256 public wantPid;

    IERC20Upgradeable public token0;
    IERC20Upgradeable public token1;

    mapping(address => mapping(address => address[])) public tokenSwapPaths;

    event HarvestState(
        uint256 cakeHarvested,
        uint256 cakeSold,
        uint256 toStrategist,
        uint256 toGovernance,
        uint256 wantCompounded,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 cakeHarvested;
        uint256 cakeSold;
        uint256 toStrategist;
        uint256 toGovernance;
        uint256 wantCompounded;
    }

    struct TokenSwapData {
        address tokenIn;
        uint256 totalSold;
        uint256 convertedToToken0;
        uint256 convertedToToken1;
        uint256 lpGained;
    }

    struct TendData {
        uint256 cakeTended;
    }

    event WithdrawState(uint256 toWithdraw, uint256 preWant, uint256 postWant, uint256 withdrawn);
    event TokenSwapPathSet(address tokenIn, address tokenOut, address[] path);
    event TokenSwap(address tokenIn, uint256 totalSold, uint256 convertedToToken0, uint256 convertedToToken1, uint256 lpGained);

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[3] memory _wantConfig,
        uint256[3] memory _feeConfig,
        uint256 _wantPid
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        token0 = IERC20Upgradeable(_wantConfig[1]);
        token1 = IERC20Upgradeable(_wantConfig[2]);

        wantPid = _wantPid;

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Approve Chef for want and cake staking
        IERC20Upgradeable(want).approve(address(chef), uint256(-1));
        cake.approve(address(chef), uint256(-1));
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.1";
    }

    function getName() external override pure returns (string memory) {
        return "StrategyPancakeLpOptimizer";
    }

    function balanceOfPool() public override view returns (uint256) {
        (uint256 staked, ) = chef.userInfo(wantPid, address(this));
        return staked;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](5);
        protectedTokens[0] = want;
        protectedTokens[1] = address(cake);
        protectedTokens[2] = address(syrup);
        protectedTokens[3] = address(token0);
        protectedTokens[4] = address(token1);
        return protectedTokens;
    }

    function isTendable() public override view returns (bool) {
        return true;
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

    function setWantPid(uint256 _wantPid) external {
        _onlyGovernance();
        wantPid = _wantPid;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(cake) != _asset, "cake");
        require(address(syrup) != _asset, "syrup");
        require(address(token0) != _asset, "token0");
        require(address(token1) != _asset, "token1");
    }

    /// @dev Deposit Badger into the staking contract
    /// @dev Track balance in the StakingRewards
    function _deposit(uint256 _want) internal override {
        // Deposit want into pancake chef
        chef.deposit(wantPid, _want);
    }

    /// @dev Unroll from all strategy positions, and transfer non-core tokens to controller rewards
    function _withdrawAll() internal override {
        // === Withdraw all Cake from Chef ===
        (uint256 cakeStaked, ) = chef.userInfo(cakePid, address(this));
        chef.leaveStaking(cakeStaked);

        // === Withdraw all Want from Chef ===
        (uint256 staked, ) = chef.userInfo(wantPid, address(this));
        chef.withdraw(wantPid, staked);

        // === Transfer extra token: Cake ===
        uint256 _cake = cake.balanceOf(address(this));
        cake.safeTransfer(IController(controller).rewards(), _cake);

        // Note: All want is automatically withdrawn outside this "inner hook" in base strategy function
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // Get idle want in the strategy
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        // If we lack sufficient idle want, withdraw the difference from the strategy position
        if (_preWant < _amount) {
            uint256 _toWithdraw = _amount.sub(_preWant);

            chef.withdraw(wantPid, _toWithdraw);

            // Note: Withdrawl process will earn Cake, this will be staked on next tend
        }

        // Confirm how much want we actually end up with
        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        uint256 _withdrawn = MathUpgradeable.min(_postWant, _amount);

        emit WithdrawState(_amount, _preWant, _postWant, _withdrawn);

        return _withdrawn;
    }

    /// @notice Harvest cake gains from Chef and deposit into SushiBar (xSushi) to increase gains
    /// @notice Any excess Sushi sitting in the Strategy will be staked as well
    /// @notice The more frequent the tend, the higher returns will be
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // ===== Harvest Cake from Want staking =====
        // Note: Deposit of zero harvests rewards balance.
        chef.deposit(wantPid, 0);
        uint256 cakeFromWant = cake.balanceOf(address(this));

        // ===== Stake Cake from previous harvest + pending value =====
        // Note: Prior to staking during enterStaking(), the pending rewards are granted to the user. So, we can staking the pending reward amount here.
        uint256 pendingCake = chef.pendingCake(cakePid, address(this));
        chef.enterStaking(cakeFromWant.add(pendingCake));

        tendData.cakeTended = cakeFromWant.add(pendingCake);
        emit Tend(tendData.cakeTended);

        return tendData;
    }

    /// @dev Harvest accumulated cake rewards and convert them to LP tokens
    /// @dev Restake gained LP tokens in chef
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 cakeBeforeHarvest = cake.balanceOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));

        // ===== Harvest cake rewards from Cake staking =====
        (uint256 cakeStaked, ) = chef.userInfo(cakePid, address(this));
        chef.leaveStaking(cakeStaked);

        // ===== Harvest Cake rewards from Want staking =====
        (uint256 staked, ) = chef.userInfo(wantPid, address(this));
        chef.deposit(wantPid, 0);

        uint256 cakeAfterHarvest = cake.balanceOf(address(this));
        harvestData.cakeHarvested = cakeAfterHarvest.sub(cakeBeforeHarvest);

        harvestData.cakeSold = cake.balanceOf(address(this));
        _sellTokenForWant(address(cake), harvestData.cakeSold);

        // ===== Deposit gained LP position into Chef =====
        uint256 lpAfterSell = IERC20Upgradeable(want).balanceOf(address(this));

        // Process performance fees in LP token
        harvestData.toStrategist = _processFee(want, lpAfterSell, performanceFeeStrategist, strategist);
        harvestData.toGovernance = _processFee(want, lpAfterSell, performanceFeeGovernance, IController(controller).rewards());

        harvestData.wantCompounded = IERC20Upgradeable(want).balanceOf(address(this));

        if (harvestData.wantCompounded > 0) {
            _deposit(harvestData.wantCompounded);
        }

        emit HarvestState(
            harvestData.cakeHarvested,
            harvestData.cakeSold,
            harvestData.toStrategist,
            harvestData.toGovernance,
            harvestData.wantCompounded,
            block.timestamp,
            block.number
        );

        emit Harvest(harvestData.wantCompounded, block.number);

        return harvestData;
    }

    // ===== Internal Helper Functions =====

    /// @dev Path must be set to sell token for want
    function _sellTokenForWant(address tokenIn, uint256 amount) internal returns (TokenSwapData memory) {
        TokenSwapData memory swapData;

        uint256 lpBefore = IERC20Upgradeable(want).balanceOf(address(this));

        swapData.tokenIn = tokenIn;
        swapData.totalSold = amount;
        swapData.convertedToToken0 = amount.div(2);
        swapData.convertedToToken1 = swapData.totalSold.sub(swapData.convertedToToken0);

        // Swap half of amount for token0
        if (swapData.convertedToToken0 > 0) {
            _swap_pancakeswap(tokenIn, swapData.convertedToToken0, getTokenSwapPath(tokenIn, address(token0)));
        }

        // Swap remaining for token1
        if (swapData.convertedToToken1 > 0) {
            _swap_pancakeswap(tokenIn, swapData.convertedToToken1, getTokenSwapPath(tokenIn, address(token1)));
        }

        // Add maximum liquidity for tokens
        _add_max_liquidity_pancakeswap(address(token0), address(token1));

        uint256 lpAfter = IERC20Upgradeable(want).balanceOf(address(this));

        swapData.lpGained = lpAfter.sub(lpBefore);

        emit TokenSwap(swapData.tokenIn, swapData.totalSold, swapData.convertedToToken0, swapData.convertedToToken1, swapData.lpGained);
    }
}
