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

contract StrategyCurveRenBTC {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant want = 0x49849C98ae39Fff122806C06791Fa73784FB3675; // Want: Curve.fi renBTC/wBTC (crvRenWBTC) LP token
    address public constant gauge = 0xB1F2cdeC61db658F091671F5f199635aEF202CAC; // Curve renBtc Gauge
    address public constant mintr = 0xd061D61a4d941c39E5453435B6345Dc261C2fcE0; // Curve CRV Minter
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant univ2Router2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Dex
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route
    
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // wBTC Token
    address public constant curveRenBtcSwap = 0x93054188d876f558f4a66B2EF1d97d16eDf0895B; // Curve renBtc Swap

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
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        if (_want > 0) {
            IERC20Upgradeable(want).safeApprove(gauge, 0);
            IERC20Upgradeable(want).safeApprove(gauge, _want);
            ICurveGauge(gauge).deposit(_want);
        }
    }

    // Controller only function for creating additional rewards from dust
    function withdrawOther(address _asset) external returns (uint256 balance) {
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
        uint256 _balance = IERC20Upgradeable(want).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _withdrawSome(_amount.sub(_balance));
            _amount = _amount.add(_balance);
        }

        uint256 _fee = _amount.mul(withdrawalFee).div(withdrawalMax);

        IERC20Upgradeable(want).safeTransfer(IController(controller).rewards(), _fee);
        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds

        IERC20Upgradeable(want).safeTransfer(_vault, _amount.sub(_fee));
    }

    // Withdraw all funds, normally used when migrating strategies
    function withdrawAll() external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        _withdrawAll();

        balance = IERC20Upgradeable(want).balanceOf(address(this));

        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds
        IERC20Upgradeable(want).safeTransfer(_vault, balance);
    }

    function _withdrawAll() internal {
        ICurveGauge(gauge).withdraw(ICurveGauge(gauge).balanceOf(address(this)));
    }

    function harvest() public {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");
        IMintr(mintr).mint(gauge);
        uint256 _crv = IERC20Upgradeable(crv).balanceOf(address(this));

        uint256 _keepCRV = _crv.mul(keepCRV).div(keepCRVMax);
        IERC20Upgradeable(crv).safeTransfer(IController(controller).rewards(), _keepCRV);
        _crv = _crv.sub(_keepCRV);

        if (_crv > 0) {
            IERC20Upgradeable(crv).safeApprove(univ2Router2, 0);
            IERC20Upgradeable(crv).safeApprove(univ2Router2, _crv);

            address[] memory path = new address[](3);
            path[0] = crv;
            path[1] = weth;
            path[2] = wbtc;

            IUniswapRouterV2(univ2Router2).swapExactTokensForTokens(_crv, uint256(0), path, address(this), now.add(1800));
        }
        uint256 _wbtc = IERC20Upgradeable(wbtc).balanceOf(address(this));
        if (_wbtc > 0) {
            IERC20Upgradeable(wbtc).safeApprove(curveRenBtcSwap, 0);
            IERC20Upgradeable(wbtc).safeApprove(curveRenBtcSwap, _wbtc);
            ICurveFi(curveRenBtcSwap).add_liquidity([0, _wbtc, 0], 0);
        }
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        if (_want > 0) {
            uint256 _fee = _want.mul(performanceFee).div(performanceMax);
            IERC20Upgradeable(want).safeTransfer(IController(controller).rewards(), _fee);
            deposit();
        }
    }

    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        ICurveGauge(gauge).withdraw(_amount);
        return _amount;
    }

    function balanceOfWant() public view returns (uint256) {
        return IERC20Upgradeable(want).balanceOf(address(this));
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
