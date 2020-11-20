// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

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

contract StrategyCurveGauge is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // IERC20Upgradeable public want = 0x49849C98ae39Fff122806C06791Fa73784FB3675; // Want: Curve.fi renBTC/wBTC (crvRenWBTC) LP token
    // address public constant gauge = 0xB1F2cdeC61db658F091671F5f199635aEF202CAC; // Curve renBtc Gauge
    // address public constant mintr = 0xd061D61a4d941c39E5453435B6345Dc261C2fcE0; // Curve CRV Minter
    // address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    // address public constant uniswap = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Dex
    // address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route

    // address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // wBTC Token
    // address public constant curveSwap = 0x93054188d876f558f4a66B2EF1d97d16eDf0895B; // Curve renBtc Swap

    address public gauge; // Curve renBtc Gauge
    address public mintr; // Curve CRV Minter
    address public curveSwap; // Curve renBtc Swap
    address public lpComponent; // wBTC for renCrv and sCrv

    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route

    uint256 public keepCRV;

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
    function harvest() external override {
        _onlyAuthorizedActors();

        IMintr(mintr).mint(address(gauge));
        uint256 _crv = IERC20Upgradeable(crv).balanceOf(address(this));

        uint256 _keepCRV = _crv.mul(keepCRV).div(MAX_FEE);
        IERC20Upgradeable(crv).safeTransfer(IController(controller).rewards(), _keepCRV);
        _crv = _crv.sub(_keepCRV);

        if (_crv > 0) {
            _safeApproveHelper(crv, uniswap, _crv);

            address[] memory path = new address[](3);
            path[0] = crv;
            path[1] = weth;
            path[2] = lpComponent;

            IUniswapRouterV2(uniswap).swapExactTokensForTokens(_crv, uint256(0), path, address(this), now.add(1800));
        }
        uint256 _lpComponent = IERC20Upgradeable(lpComponent).balanceOf(address(this));
        if (_lpComponent > 0) {
            _safeApproveHelper(lpComponent, curveSwap, _lpComponent);
            ICurveFi(curveSwap).add_liquidity([0, _lpComponent, 0], 0);
        }
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        if (_want > 0) {
            uint256 _strategistFee = _want.mul(performanceFeeStrategist).div(MAX_FEE);
            uint256 _governanceFee = _want.mul(performanceFeeGovernance).div(MAX_FEE);

            IERC20Upgradeable(want).safeTransfer(strategist, _strategistFee);
            IERC20Upgradeable(want).safeTransfer(IController(controller).rewards(), _governanceFee);

            _deposit(_want);
        }
    }
}
