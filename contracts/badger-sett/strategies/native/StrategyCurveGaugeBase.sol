// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "../BaseStrategy.sol";

contract StrategyCurveGaugeBase is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public gauge; // Curve renBtc Gauge
    address public mintr; // Curve CRV Minter
    address public curveSwap; // Curve renBtc Swap
    address public lpComponent; // wBTC for renCrv and sCrv

    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // Wbtc Token

    uint256 public keepCRV;

    event CurveHarvest(
        uint256 crvHarvested,
        uint256 keepCrv,
        uint256 crvRecycled,
        uint256 lpComponentDeposited,
        uint256 wantProcessed,
        uint256 wantDeposited,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee
    );

    struct HarvestData {
        uint256 crvHarvested;
        uint256 keepCrv;
        uint256 crvRecycled;
        uint256 lpComponentDeposited;
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
        address[5] memory _wantConfig,
        uint256[4] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        gauge = _wantConfig[1];
        mintr = _wantConfig[2];
        curveSwap = _wantConfig[3];
        lpComponent = _wantConfig[4];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        keepCRV = _feeConfig[3]; // 1000

        IERC20Upgradeable(want).safeApprove(gauge, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyCurveGauge";
    }

    function balanceOfPool() public override view returns (uint256) {
        return ICurveGauge(gauge).balanceOf(address(this));
    }

    function getProtectedTokens() external view override returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = lpComponent;
        protectedTokens[2] = crv;
        return protectedTokens;
    }

    /// ===== Permissioned Actions: Governance =====
    function setKeepCRV(uint256 _keepCRV) external {
        _onlyGovernance();
        keepCRV = _keepCRV;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(lpComponent != _asset, "lpComponent");
        require(crv != _asset, "crv");
    }

    function _deposit(uint256 _want) internal override {
        ICurveGauge(gauge).deposit(_want);
    }

    function _withdrawAll() internal override {
        ICurveGauge(gauge).withdraw(ICurveGauge(gauge).balanceOf(address(this)));
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        ICurveGauge(gauge).withdraw(_amount);
        return _amount;
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeCrv = IERC20Upgradeable(want).balanceOf(address(this));

        // Harvest from Gauge
        IMintr(mintr).mint(address(gauge));
        uint256 _afterCrv = IERC20Upgradeable(crv).balanceOf(address(this));

        harvestData.crvHarvested = _afterCrv.sub(_beforeCrv);
        uint256 _crv = _afterCrv;

        // Transfer CRV to keep to Rewards
        harvestData.keepCrv = _crv.mul(keepCRV).div(MAX_FEE);
        IERC20Upgradeable(crv).safeTransfer(IController(controller).rewards(), harvestData.keepCrv);

        harvestData.crvRecycled = _crv.sub(harvestData.keepCrv);

        // Convert remaining CRV to lpComponent
        if (harvestData.crvRecycled > 0) {
            address[] memory path = new address[](3);
            path[0] = crv;
            path[1] = weth;
            path[2] = lpComponent;
            _swap(crv, harvestData.crvRecycled, path);
        }

        // Deposit into Curve to increase LP position
        harvestData.lpComponentDeposited = IERC20Upgradeable(lpComponent).balanceOf(address(this));
        if (harvestData.lpComponentDeposited > 0) {
            _safeApproveHelper(lpComponent, curveSwap, harvestData.lpComponentDeposited);
            _add_liquidity_curve(harvestData.lpComponentDeposited);
        }

        // Take fees from LP increase, and deposit remaining into Gauge
        harvestData.wantProcessed = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.wantProcessed > 0) {
            uint256 _strategistFee = harvestData.wantProcessed.mul(performanceFeeStrategist).div(MAX_FEE);
            uint256 _governanceFee = harvestData.wantProcessed.mul(performanceFeeGovernance).div(MAX_FEE);

            (harvestData.governancePerformanceFee, harvestData.strategistPerformanceFee) = _processPerformanceFees(harvestData.wantProcessed);

            // Deposit remaining want into Gauge
            harvestData.wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));

            if (harvestData.wantDeposited > 0) {
                _deposit(harvestData.wantDeposited);
            }
        }

        emit CurveHarvest(
            harvestData.crvHarvested,
            harvestData.keepCrv,
            harvestData.crvRecycled,
            harvestData.lpComponentDeposited,
            harvestData.wantProcessed,
            harvestData.wantDeposited,
            harvestData.governancePerformanceFee,
            harvestData.strategistPerformanceFee
        );
        emit Harvest(harvestData.wantProcessed.sub(_before), block.number);

        return harvestData;
    }

    /// ===== Internal Helper Functions =====

    /// @dev Handle the particular function variant for CurveSwap
    function _add_liquidity_curve(uint256 _amount) internal virtual {
        // e.g. ICurveFi(curveSwap).add_liquidity([0, _amount, 0], 0);
    }

    function _processPerformanceFees(uint256 _amount) internal returns(uint256 governancePerformanceFee, uint256 strategistPerformanceFee) {
            governancePerformanceFee = _processFee(
                want,
                _amount,
                performanceFeeGovernance,
                IController(controller).rewards()
            );

            strategistPerformanceFee = _processFee(want, _amount, performanceFeeStrategist, strategist);
    }
}
