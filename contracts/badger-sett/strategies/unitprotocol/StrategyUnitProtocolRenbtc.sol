pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../../../../interfaces/curve/ICurveGauge.sol";
import "../../../../interfaces/curve/ICurveMintr.sol";
import "../../../../interfaces/curve/ICurveFi.sol";
import "../../../../interfaces/curve/ICurveExchange.sol";

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

    // yield-farming in usdp-3crv pool
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52;
    address public constant usdp3crv = 0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6;
    address public constant usdp = 0x1456688345527bE1f37E9e627DA0837D6f08C925;
    address public constant usdp_gauge = 0x055be5DDB7A925BfEF3417FC157f53CA77cA7222;
    address public constant curvePool = 0x42d7025938bEc20B69cBae5A77421082407f053A;
    address public constant mintr = 0xd061D61a4d941c39E5453435B6345Dc261C2fcE0;

    // slippage protection for one-sided ape in/out
    uint256 public slippageProtectionIn = 50; // max 0.5%
    uint256 public slippageProtectionOut = 50; // max 0.5%
    uint256 public keepCRV;

    event RenBTCStratHarvest(
        uint256 crvHarvested,
        uint256 keepCrv,
        uint256 crvRecycled,
        uint256 wantProcessed,
        uint256 wantDeposited,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee
    );

    struct HarvestData {
        uint256 crvHarvested;
        uint256 keepCrv;
        uint256 crvRecycled;
        uint256 wantProcessed;
        uint256 wantDeposited;
        uint256 governancePerformanceFee;
        uint256 strategistPerformanceFee;
    }

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

        minRatio = 200;
        ratioBuff = 200;
    }

    // **** Setters ****

    function setSlippageProtectionIn(uint256 _slippage) external {
        _onlyGovernance();
        slippageProtectionIn = _slippage;
    }

    function setSlippageProtectionOut(uint256 _slippage) external {
        _onlyGovernance();
        slippageProtectionOut = _slippage;
    }

    function setKeepCRV(uint256 _keepCRV) external {
        _onlyGovernance();
        keepCRV = _keepCRV;
    }

    // **** State Mutation functions ****

    function getHarvestable() external returns (uint256) {
        return ICurveGauge(usdp_gauge).claimable_tokens(address(this));
    }

    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeCrv = IERC20Upgradeable(crv).balanceOf(address(this));

        // Harvest from Gauge
        ICurveMintr(mintr).mint(usdp_gauge);
        uint256 _afterCrv = IERC20Upgradeable(crv).balanceOf(address(this));

        harvestData.crvHarvested = _afterCrv.sub(_beforeCrv);
        uint256 _crv = _afterCrv;

        // Transfer CRV to keep to Rewards
        harvestData.keepCrv = _crv.mul(keepCRV).div(MAX_FEE);
        IERC20Upgradeable(crv).safeTransfer(IController(controller).rewards(), harvestData.keepCrv);

        harvestData.crvRecycled = _crv.sub(harvestData.keepCrv);

        if (harvestData.crvRecycled > 0) {
            address[] memory path = new address[](3);
            path[0] = crv;
            path[1] = weth;
            path[2] = want;
            _swap(crv, harvestData.crvRecycled, path);
        }

        // Take fees from want increase, and deposit remaining into Gauge
        harvestData.wantProcessed = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.wantProcessed > 0) {
            (harvestData.governancePerformanceFee, harvestData.strategistPerformanceFee) = _processPerformanceFees(harvestData.wantProcessed);

            // Reinvest remaining want
            harvestData.wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));

            if (harvestData.wantDeposited > 0) {
                _deposit(harvestData.wantDeposited);
            }
        }

        emit RenBTCStratHarvest(
            harvestData.crvHarvested,
            harvestData.keepCrv,
            harvestData.crvRecycled,
            harvestData.wantProcessed,
            harvestData.wantDeposited,
            harvestData.governancePerformanceFee,
            harvestData.strategistPerformanceFee
        );

        emit Harvest(harvestData.wantProcessed.sub(_before), block.number);

        return harvestData;
    }

    function _processPerformanceFees(uint256 _amount) internal returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee) {
        governancePerformanceFee = _processFee(want, _amount, performanceFeeGovernance, IController(controller).rewards());
        strategistPerformanceFee = _processFee(want, _amount, performanceFeeStrategist, strategist);
    }

    function _depositUSDP(uint256 _usdpAmt) internal override {
        if (_usdpAmt > 0 && checkSlip(_usdpAmt)) {
            _safeApproveHelper(usdp, curvePool, _usdpAmt);
            uint256[2] memory amounts = [_usdpAmt, 0];
            ICurveFi(curvePool).add_liquidity(amounts, 0);
        }

        uint256 _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        if (_usdp3crv > 0) {
            _safeApproveHelper(usdp3crv, usdp_gauge, _usdp3crv);
            ICurveGauge(usdp_gauge).deposit(_usdp3crv);
        }
    }

    function _withdrawUSDP(uint256 _usdpAmt) internal override {
        uint256 _requiredUsdp3crv = estimateRequiredUsdp3crv(_usdpAmt);
        _requiredUsdp3crv = _requiredUsdp3crv.mul(MAX_FEE.add(slippageProtectionOut)).div(MAX_FEE); // try to remove bit more

        uint256 _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        uint256 _withdrawFromGauge = _usdp3crv < _requiredUsdp3crv ? _requiredUsdp3crv.sub(_usdp3crv) : 0;

        if (_withdrawFromGauge > 0) {
            uint256 maxInGauge = ICurveGauge(usdp_gauge).balanceOf(address(this));
            ICurveGauge(usdp_gauge).withdraw(maxInGauge < _withdrawFromGauge ? maxInGauge : _withdrawFromGauge);
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
        uint256 p = ICurveFi(curvePool).get_virtual_price();
        require(p > 0, "!p");
        return p;
    }

    function estimateRequiredUsdp3crv(uint256 _usdpAmt) public view returns (uint256) {
        uint256[2] memory amounts = [_usdpAmt, 0];
        return ICurveExchange(curvePool).calc_token_amount(amounts, false);
    }

    function checkSlip(uint256 _usdpAmt) public view returns (bool) {
        uint256 expectedOut = _usdpAmt.mul(1e18).div(virtualPriceToWant());
        uint256 maxSlip = expectedOut.mul(MAX_FEE.sub(slippageProtectionIn)).div(MAX_FEE);

        uint256[2] memory amounts = [_usdpAmt, 0];
        return ICurveExchange(curvePool).calc_token_amount(amounts, true) >= maxSlip;
    }

    function usdpOfPool() public view returns (uint256) {
        uint256 _usdp3crv = IERC20Upgradeable(usdp3crv).balanceOf(address(this));
        _usdp3crv = _usdp3crv.add(ICurveGauge(usdp_gauge).balanceOf(address(this)));
        return usdp3crvToUsdp(_usdp3crv);
    }

    function usdp3crvToUsdp(uint256 _usdp3crv) public view returns (uint256) {
        if (_usdp3crv == 0) {
            return 0;
        }
        // use underestimate of current assets.
        uint256 virtualOut = virtualPriceToWant().mul(_usdp3crv).div(1e18);
        uint256 realOut = ICurveFi(curvePool).calc_withdraw_one_coin(_usdp3crv, 0);
        return virtualOut > realOut ? realOut : virtualOut;
    }

    /// @notice Specify tokens used in yield process, should not be available to withdraw via withdrawOther()
    function _onlyNotProtectedTokens(address _asset) internal override {
        require(usdp3crv != _asset, "!usdp3crv");
        require(usdp != _asset, "!usdp");
        require(renbtc_collateral != _asset, "!usdp");
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = renbtc_collateral;
        protectedTokens[1] = usdp;
        protectedTokens[2] = usdp3crv;
        return protectedTokens;
    }

    /// @dev User-friendly name for this strategy for purposes of convenient reading
    function getName() external override pure returns (string memory) {
        return "StrategyUnitProtocolRenbtc";
    }
}
