pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../../../../interfaces/curve/ICurveGauge.sol";
import "../../../../interfaces/curve/ICurveMintr.sol";
import "../../../../interfaces/curve/ICurveFi.sol";
import "../../../../interfaces/curve/ICurveExchange.sol";

import "../../../../interfaces/chainlink/IChainlink.sol";

import "../../../../interfaces/convex/IBaseRewardsPool.sol";
import "../../../../interfaces/convex/IBooster.sol";
import "../../../../interfaces/convex/ICvxMinter.sol";

import "./StrategyUnitProtocolMeta.sol";

contract StrategyUnitProtocolRenbtc is StrategyUnitProtocolMeta {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // strategy specific
    address public constant renbtc_collateral = 0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D;
    uint256 public constant renbtc_collateral_decimal = 1e8;
    address public constant renbtc_oracle = 0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c;
    uint256 public constant renbtc_price_decimal = 1;
    bool public constant renbtc_price_eth = false;
    bool public harvestToRepay = false;

    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    uint256 public constant weth_decimal = 1e18;
    address public constant usdp3crv = 0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6;
    address public constant usdp = debtToken;
    address public constant curvePool = 0x42d7025938bEc20B69cBae5A77421082407f053A;
    uint256 public constant usdp_decimal = 1e18;
	
    // yield-farming in usdp-3crv pool & Convex Finance
    address public stakingPool = 0xF403C135812408BFbE8713b5A23a04b3D48AAE31;
    uint256 public stakingPoolId = 28;
    address public constant rewardTokenCRV = 0xD533a949740bb3306d119CC777fa900bA034cd52; 
    address public constant rewardTokenCVX = 0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B;
    address public rewardPool = 0x24DfFd1949F888F91A0c8341Fc98a3F280a782a8;
    
    // slippage protection for one-sided ape in/out
    uint256 public slippageRepayment = 500; // max 5%
    uint256 public slippageProtectionIn = 50; // max 0.5%
    uint256 public slippageProtectionOut = 50; // max 0.5%
    uint256 public keepCRV;
    uint256 public keepCVX;

    event RenBTCStratHarvest(
        uint256 crvHarvested,
        uint256 cvxHarvested,
        uint256 usdpRepaid,
        uint256 wantProcessed,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee
    );

    struct HarvestData {
        uint256 crvHarvested;
        uint256 cvxHarvested;
        uint256 usdpRepaid;
        uint256 wantProcessed;
        uint256 governancePerformanceFee;
        uint256 strategistPerformanceFee;
    }

    //
    // feeConfig: governance/strategist/withdrawal/keepCRV
    //   
    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[1] memory _wantConfig,
        uint256[4] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        require(_wantConfig[0] == renbtc_collateral, "!want");
        want = _wantConfig[0];
        collateral = renbtc_collateral;
        collateralDecimal = renbtc_collateral_decimal;
        unitOracle = renbtc_oracle;
        collateralPriceDecimal = renbtc_price_decimal;
        collateralPriceEth = renbtc_price_eth;

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        keepCRV = _feeConfig[3];
        keepCVX = keepCRV;
		
        // avoid empty value after clones
        minRatio = 150;
        ratioBuff = 200;
        useUnitUsdOracle = true;
        dustMinDebt = 10000;
		
        slippageRepayment = 500;
        slippageProtectionIn = 50;
        slippageProtectionOut = 50;
        stakingPoolId = 28;
    }

    // **** Setters ****
    
    function setSlippageRepayment(uint256 _repaymentSlippage) public{
        _onlyGovernance();
        require(_repaymentSlippage < MAX_FEE && _repaymentSlippage > 0, "!_repaymentSlippage");
        slippageRepayment = _repaymentSlippage;
    }

    function setStakingPoolId(uint256 _poolId) public{
        _onlyGovernance();
        stakingPoolId = _poolId;
    }

    function setStakingPool(address _pool) public{
        _onlyGovernance();
        stakingPool = _pool;
    }

    function setRewardPool(address _pool) public{
        _onlyGovernance();
        rewardPool = _pool;
    }

    function setSlippageProtectionIn(uint256 _slippage) external {
        _onlyGovernance();
        require(_slippage < MAX_FEE && _slippage > 0, "!_slippageProtectionIn");
        slippageProtectionIn = _slippage;
    }

    function setSlippageProtectionOut(uint256 _slippage) external {
        _onlyGovernance();
        require(_slippage < MAX_FEE && _slippage > 0, "!_slippageProtectionOut");
        slippageProtectionOut = _slippage;
    }

    function setKeepCRV(uint256 _keepCRV) external {
        _onlyGovernance();
        keepCRV = _keepCRV;
    }

    function setKeepCVX(uint256 _keepCVX) external {
        _onlyGovernance();
        keepCVX = _keepCVX;
    }

    function setHarvestToRepay(bool _repay) public{
        _onlyGovernance();
        harvestToRepay = _repay;
    }

    // **** State Mutation functions ****

    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;
        (uint256 _crvRecycled, uint256 _cvxRecycled) = _collectStakingRewards(harvestData);
				
        // Convert CRV & CVX Rewards to WETH
        _convertRewards();
		
        // Repay borrowed debt
        uint256 _wethAmount = IERC20Upgradeable(weth).balanceOf(address(this));
        if (_wethAmount > 0){         
            harvestData.usdpRepaid = _repayDebt(_wethAmount); 
        }
		
        // Convert WETH to Want for reinvestement
        _wethAmount = IERC20Upgradeable(weth).balanceOf(address(this));
        if (_wethAmount > 0 && !harvestToRepay) {
            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = want;
            _swapExactTokensForTokens(uniswap, weth, _wethAmount, path);
        }

        // Take fees from want increase, and deposit remaining
        harvestData.wantProcessed = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _wantDeposited;
        if (harvestData.wantProcessed > 0 && !harvestToRepay) {
            (harvestData.governancePerformanceFee, harvestData.strategistPerformanceFee) = _processPerformanceFees(harvestData.wantProcessed);

            // Reinvest remaining want
            _wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));

            if (_wantDeposited > 0) {
                _deposit(_wantDeposited);
            }
        }

        emit RenBTCStratHarvest(harvestData.crvHarvested, harvestData.cvxHarvested, harvestData.usdpRepaid, harvestData.wantProcessed, harvestData.governancePerformanceFee, harvestData.strategistPerformanceFee);
        emit Harvest(_wantDeposited, block.number);

        return harvestData;
    }
	
    function _collectStakingRewards(HarvestData memory harvestData) internal returns(uint256, uint256){
        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeCrv = IERC20Upgradeable(rewardTokenCRV).balanceOf(address(this));
        uint256 _beforeCvx = IERC20Upgradeable(rewardTokenCVX).balanceOf(address(this));

        // Harvest from Convex Finance
        IBaseRewardsPool(rewardPool).getReward(address(this), true);
		
        uint256 _afterCrv = IERC20Upgradeable(rewardTokenCRV).balanceOf(address(this));
        uint256 _afterCvx = IERC20Upgradeable(rewardTokenCVX).balanceOf(address(this));

        harvestData.crvHarvested = _afterCrv.sub(_beforeCrv);
        harvestData.cvxHarvested = _afterCvx.sub(_beforeCvx);
        
        uint256 _crv = _afterCrv;
        uint256 _cvx = _afterCvx;

        // Transfer CRV & CVX token to Rewards wallet as configured
        uint256 _keepCrv = _crv.mul(keepCRV).div(MAX_FEE);
        uint256 _keepCvx = _cvx.mul(keepCVX).div(MAX_FEE);        
        IERC20Upgradeable(rewardTokenCRV).safeTransfer(IController(controller).rewards(), _keepCrv);
        IERC20Upgradeable(rewardTokenCVX).safeTransfer(IController(controller).rewards(), _keepCvx);

        uint256 _crvRecycled = _crv.sub(_keepCrv);
        uint256 _cvxRecycled = _cvx.sub(_keepCvx);
        return (_crvRecycled, _cvxRecycled);
    }
	
    function _repayDebt(uint256 _wethAmount) internal returns(uint256) {
        uint256 _repaidDebt;
        if (harvestToRepay){
            // Repay debt ONLY to skip reinvest in case of strategy migration period 
            _repaidDebt = _swapRewardsToDebt(_wethAmount);                
        } else {		
            // Repay debt first
            uint256 dueFee = getDueFee();
            if (dueFee > 0){		
                uint256 _swapIn = calcETHSwappedForFeeRepayment(dueFee, _wethAmount);			
                _repaidDebt = _swapRewardsToDebt(_swapIn);
				
                require(IERC20Upgradeable(debtToken).balanceOf(address(this)) >= dueFee, '!notEnoughRepaymentDuringHarvest');
				
                uint256 debtTotalBefore = getDebtBalance();
                repayAndRedeemCollateral(0, dueFee);
                require(getDebtBalance() < debtTotalBefore, '!repayDebtDuringHarvest');
            }			
        }
        return _repaidDebt;
    }
	
    function _convertRewards() internal {		
        uint256 _rewardCRV = IERC20Upgradeable(rewardTokenCRV).balanceOf(address(this));
        uint256 _rewardCVX = IERC20Upgradeable(rewardTokenCVX).balanceOf(address(this));

        if (_rewardCRV > 0) {
            address[] memory _swapPath = new address[](2);
            _swapPath[0] = rewardTokenCRV;
            _swapPath[1] = weth;
            _swapExactTokensForTokens(sushiswap, rewardTokenCRV, _rewardCRV, _swapPath);
        }

        if (_rewardCVX > 0) {
            address[] memory _swapPath = new address[](2);
            _swapPath[0] = rewardTokenCVX;
            _swapPath[1] = weth;
            _swapExactTokensForTokens(sushiswap, rewardTokenCVX, _rewardCVX, _swapPath);
        }
    }
	
    function _swapRewardsToDebt(uint256 _swapIn) internal returns (uint256){
        address[] memory _swapPath = new address[](2);
        _swapPath[0] = weth;
        _swapPath[1] = debtToken;
        uint256 _beforeDebt = IERC20Upgradeable(debtToken).balanceOf(address(this));
        _swapExactTokensForTokens(sushiswap, weth, _swapIn, _swapPath);
        return IERC20Upgradeable(debtToken).balanceOf(address(this)).sub(_beforeDebt);
    }
	
    function calcETHSwappedForFeeRepayment(uint256 _dueFee, uint256 _toSwappedETHBal) public view returns (uint256){
        (,int ethPrice,,,) = IChainlinkAggregator(eth_usd).latestRoundData();// eth price from chainlink in 1e8 decimal
        uint256 toSwapped = _dueFee.mul(weth_decimal).div(usdp_decimal).mul(1e8).div(uint256(ethPrice));
        uint256 _swapIn = toSwapped.mul(MAX_FEE.add(slippageRepayment)).div(MAX_FEE);
        return _swapIn > _toSwappedETHBal ? _toSwappedETHBal : _swapIn;
    }

    function _processPerformanceFees(uint256 _amount) internal returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee) {
        governancePerformanceFee = _processFee(want, _amount, performanceFeeGovernance, IController(controller).rewards());
        strategistPerformanceFee = _processFee(want, _amount, performanceFeeStrategist, strategist);
    }

    function estimateMinCrvLPFromDeposit(uint256 _usdpAmt) public view returns(uint256){
        uint256 _expectedOut = estimateRequiredUsdp3crv(_usdpAmt);
        _expectedOut = _expectedOut.mul(MAX_FEE.sub(slippageProtectionIn)).div(MAX_FEE);
        return _expectedOut;
    }

    function _depositUSDP(uint256 _usdpAmt) internal override {
        uint256 _maxSlip = estimateMinCrvLPFromDeposit(_usdpAmt);
        if (_usdpAmt > 0 && checkSlip(_usdpAmt, _maxSlip)) {
            _safeApproveHelper(debtToken, curvePool, _usdpAmt);
            uint256[2] memory amounts = [_usdpAmt, 0];
            ICurveFi(curvePool).add_liquidity(amounts, _maxSlip);
        }

        uint256 _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        if (_usdp3crv > 0) {
            _safeApproveHelper(usdp3crv, stakingPool, _usdp3crv);
            IBooster(stakingPool).depositAll(stakingPoolId, true);
        }
    }

    function _withdrawUSDP(uint256 _usdpAmt) internal override {
        uint256 _requiredUsdp3crv = estimateRequiredUsdp3crv(_usdpAmt);
        _requiredUsdp3crv = _requiredUsdp3crv.mul(MAX_FEE.add(slippageProtectionOut)).div(MAX_FEE); // try to remove bit more

        uint256 _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        uint256 _withdrawFromStaking = _usdp3crv < _requiredUsdp3crv ? _requiredUsdp3crv.sub(_usdp3crv) : 0;

        if (_withdrawFromStaking > 0) {
            uint256 maxInStaking = IBaseRewardsPool(rewardPool).balanceOf(address(this));
            uint256 _toWithdraw = maxInStaking < _withdrawFromStaking ? maxInStaking : _withdrawFromStaking;
            IBaseRewardsPool(rewardPool).withdrawAndUnwrap(_toWithdraw, false);
        }

        _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        if (_usdp3crv > 0) {
            _requiredUsdp3crv = _requiredUsdp3crv > _usdp3crv ? _usdp3crv : _requiredUsdp3crv;
            uint256 maxSlippage = _requiredUsdp3crv.mul(MAX_FEE.sub(slippageProtectionOut)).div(MAX_FEE);
            _safeApproveHelper(usdp3crv, curvePool, _requiredUsdp3crv);
            ICurveFi(curvePool).remove_liquidity_one_coin(_requiredUsdp3crv, 0, maxSlippage);
        }
    }

    // **** Views ****

    function virtualPriceToWant() public view returns (uint256) {
        return ICurveFi(curvePool).get_virtual_price();
    }

    function estimateRequiredUsdp3crv(uint256 _usdpAmt) public view returns (uint256) {
        return _usdpAmt.mul(1e18).div(virtualPriceToWant());
    }

    function checkSlip(uint256 _usdpAmt, uint256 _maxSlip) public view returns (bool) {
        uint256[2] memory amounts = [_usdpAmt, 0];
        return ICurveExchange(curvePool).calc_token_amount(amounts, true) >= _maxSlip;
    }	
	
    function balanceOfCrvLPToken() public view returns (uint256){
        uint256 lpAmt = IBaseRewardsPool(rewardPool).balanceOf(address(this));
        return lpAmt.add(IERC20Upgradeable(usdp3crv).balanceOf(address(this)));
    }
	
    function usdpOfPool() public view returns (uint256){
        uint256 lpAmt = balanceOfCrvLPToken();
        return usdp3crvToUsdp(lpAmt);
    }

    function usdp3crvToUsdp(uint256 _usdp3crv) public view returns (uint256) {
        if (_usdp3crv == 0) {
            return 0;
        }
        return virtualPriceToWant().mul(_usdp3crv).div(1e18);
    }

    /// @notice Specify tokens used in yield process, should not be available to withdraw via withdrawOther()
    function _onlyNotProtectedTokens(address _asset) internal override {
        require(usdp3crv != _asset, "!usdp3crv");
        require(debtToken != _asset, "!usdp");
        require(renbtc_collateral != _asset, "!renbtc");
    }

    function getProtectedTokens() public override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = renbtc_collateral;
        protectedTokens[1] = debtToken;
        protectedTokens[2] = usdp3crv;
        return protectedTokens;
    }

    /// @dev User-friendly name for this strategy for purposes of convenient reading
    function getName() external override pure returns (string memory) {
        return "StrategyUnitProtocolRenbtc";
    }

    // only include CRV earned
    function getHarvestable() public view returns (uint256) {
        return IBaseRewardsPool(rewardPool).earned(address(this));
    }
	
    // https://etherscan.io/address/0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b#code#L1091
    function mintableCVX(uint256 _amount) public view returns (uint256) {
        uint256 _toMint = 0;
        uint256 supply = IERC20Upgradeable(rewardTokenCVX).totalSupply();
        uint256 cliff = supply.div(ICvxMinter(rewardTokenCVX).reductionPerCliff());
        uint256 totalCliffs = ICvxMinter(rewardTokenCVX).totalCliffs();
        if (cliff < totalCliffs){
            uint256 reduction = totalCliffs.sub(cliff);
            _amount = _amount.mul(reduction).div(totalCliffs);
            uint256 amtTillMax = ICvxMinter(rewardTokenCVX).maxSupply().sub(supply);
            if (_amount > amtTillMax){
                _amount = amtTillMax;
            }
            _toMint = _amount;
        }
        return _toMint;
    }

    function getHarvestableCVX() public view returns (uint256) {
        uint256 _crvEarned = getHarvestable();
        return mintableCVX(_crvEarned);
    }
}
