// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";

contract StrategyCurveSBTC {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    address public constant want = 0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3; // Want: Curve sBtc LP tokens
    address public constant gauge = 0x705350c4BcD35c9441419DdD5d2f097d7a55410F; // Curve sBtc Gauge
    address public constant mintr = 0xd061D61a4d941c39E5453435B6345Dc261C2fcE0; // Curve CRV Minter
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant univ2Router2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Dex
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route

    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // wBTC Token
    address public constant sbtcCurveSwap = 0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714; // Curve Sbtc Swap

    uint256 public performanceFee = 450;
    uint256 public constant performanceMax = 10000;

    uint256 public withdrawalFee = 50;
    uint256 public constant withdrawalMax = 10000;

    uint256 public keepCRV = 1000;
    uint256 public constant keepCRVMax = 10000;

    address public governance;
    address public controller;
    address public strategist;

    constructor(
        address _governance,
        address _strategist,
        address _controller
    ) public {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;
    }

    function getName() external pure returns (string memory) {
        return "StrategyCurveSBTC";
    }

    function setStrategist(address _strategist) external {
        require(msg.sender == governance, "!governance");
        strategist = _strategist;
    }

    function setKeepCRV(uint256 _keepCRV) external {
        require(msg.sender == governance, "!governance");
        keepCRV = _keepCRV;
    }

    function setWithdrawalFee(uint256 _withdrawalFee) external {
        require(msg.sender == governance, "!governance");
        withdrawalFee = _withdrawalFee;
    }

    function setPerformanceFee(uint256 _performanceFee) external {
        require(msg.sender == governance, "!governance");
        performanceFee = _performanceFee;
    }

    function deposit() public {
        uint256 _want = IERC20(want).balanceOf(address(this));
        if (_want > 0) {
            IERC20(want).safeApprove(gauge, 0);
            IERC20(want).safeApprove(gauge, _want);
            ICurveGauge(gauge).deposit(_want);
        }
    }

    // Controller only function for creating additional rewards from dust
    function withdrawOther(IERC20 _asset) external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        require(want != _asset, "want");
        require(wbtc != _asset, "wbtc");
        require(crv != _asset, "crv");
        balance = IERC20Upgradeable(_asset).balanceOf(address(this));
        IERC20Upgradeable(_asset).safeTransfer(controller, balance);
    }

    // Withdraw partial funds, normally used with a vault withdrawal
    function withdraw(uint256 _amount) external {
        require(msg.sender == controller, "!controller");
        uint256 _balance = IERC20(want).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _withdrawSome(_amount.sub(_balance));
            _amount = _amount.add(_balance);
        }

        uint256 _fee = _amount.mul(withdrawalFee).div(withdrawalMax);

        IERC20(want).safeTransfer(IController(controller).rewards(), _fee);
        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds

        IERC20(want).safeTransfer(_vault, _amount.sub(_fee));
    }

    // Withdraw all funds, normally used when migrating strategies
    function withdrawAll() external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        _withdrawAll();

        balance = IERC20(want).balanceOf(address(this));

        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds
        IERC20(want).safeTransfer(_vault, balance);
    }

    function _withdrawAll() internal {
        ICurveGauge(gauge).withdraw(ICurveGauge(gauge).balanceOf(address(this)));
    }
    function harvest() public {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");
        IMintr(mintr).mint(gauge);
        uint256 _crv = IERC20(crv).balanceOf(address(this));

        uint256 _keepCRV = _crv.mul(keepCRV).div(keepCRVMax);
        IERC20(crv).safeTransfer(IController(controller).rewards(), _keepCRV);
        _crv = _crv.sub(_keepCRV);

        if (_crv > 0) {
            IERC20(crv).safeApprove(univ2Router2, 0);
            IERC20(crv).safeApprove(univ2Router2, _crv);

            address[] memory path = new address[](3);
            path[0] = crv;
            path[1] = weth;
            path[2] = wbtc;

            IUniswapRouterV2(univ2Router2).swapExactTokensForTokens(_crv, uint256(0), path, address(this), now.add(1800));
        }
        uint256 _wbtc = IERC20(wbtc).balanceOf(address(this));
        if (_wbtc > 0) {
            IERC20(wbtc).safeApprove(sbtcCurveSwap, 0);
            IERC20(wbtc).safeApprove(sbtcCurveSwap, _wbtc);
            ICurveFi(sbtcCurveSwap).add_liquidity([0, _wbtc, 0], 0);
        }
        uint256 _want = IERC20(want).balanceOf(address(this));
        if (_want > 0) {
            uint256 _fee = _want.mul(performanceFee).div(performanceMax);
            IERC20(want).safeTransfer(IController(controller).rewards(), _fee);
            deposit();
        }
    }

    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        ICurveGauge(gauge).withdraw(_amount);
        return _amount;
    }

    function balanceOfWant() public view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    function balanceOfPool() public view returns (uint256) {
        return ICurveGauge(gauge).balanceOf(address(this));
    }

    function balanceOf() public view returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }

    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        governance = _governance;
    }

    function setController(address _controller) external {
        require(msg.sender == governance, "!governance");
        controller = _controller;
    }
}
