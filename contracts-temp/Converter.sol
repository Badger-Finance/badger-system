// hevm: flattened sources of src/strategy-converters/curve-scrv-uni-converter.sol
pragma solidity >=0.4.23 >=0.6.0 <0.7.0 >=0.6.2 <0.7.0 >=0.6.7 <0.7.0;

////// src/interfaces/controller.sol
// SPDX-License-Identifier: MIT

/* pragma solidity ^0.6.0; */
// import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
// import "@openzeppelinV3/contracts/math/SafeMath.sol";
// import "@openzeppelinV3/contracts/utils/Address.sol";
// import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IStrategy.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/curve/ICurveMintr.sol";
import "interfaces/curve/ICurveVotingEscrow.sol";
import "interfaces/curve/ICurveZap.sol";

import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapV2Pair.sol";
import "interfaces/uniswap/IUniswapV2Factory.sol";
import "interfaces/uniswap/IStakingRewards.sol";

import "interfaces/erc20/USDT.sol";

contract CurveSCrvUniConverter {
    using SafeMath for uint256;

    // Curve's SUsdV2 Zap
    address constant zap = 0xFCBa3E75865d2d561BE8D220616520c171F12851;

    // Uniswap router
    address constant univ2Router = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;

    address constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant dai = 0x6B175474E89094C44Da98b954EedeAC495271d0F;
    address constant usdc = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant usdt = 0xdAC17F958D2ee523a2206206994597C13D831ec7;
    address constant susd = 0x57Ab1ec28D129707052df4dF418D58a2D46d5f51;

    // Converts Uni LP tokens to Uni LP tokens
    function convert(
        address _refundExcess,
        address _fromWant,
        address _toWant,
        uint256 _wantAmount
    ) external returns (uint256) {
        // 1. Gets liquidity tokens from msg.sender
        IERC20(_fromWant).transferFrom(msg.sender, address(this), _wantAmount);

        // 2. Which stablecoin do we want?
        address toStablecoin = IUniswapV2Pair(_toWant).token0() == weth
            ? IUniswapV2Pair(_toWant).token1()
            : IUniswapV2Pair(_toWant).token0();

        // 3. Removes liquidity
        IERC20(_fromWant).approve(zap, _wantAmount);
        ICurveZap(zap).remove_liquidity_one_coin(
            _wantAmount,
            _getIndex(toStablecoin),
            0
        );

        // 4. Converts half to weth
        uint256 _toConvert = IERC20(toStablecoin).balanceOf(address(this)).div(
            2
        );
        if (toStablecoin != usdt) {
            IERC20(toStablecoin).approve(univ2Router, _toConvert);
        } else {
            USDT(toStablecoin).approve(univ2Router, _toConvert);
        }
        IUniswapRouterV2(univ2Router).swapExactTokensForTokens(
            _toConvert,
            0,
            _getPath(toStablecoin),
            address(this),
            now + 60
        );

        // 5. Supplies liquidity
        IERC20(weth).approve(
            univ2Router,
            IERC20(weth).balanceOf(address(this))
        );

        if (toStablecoin != usdt) {
            IERC20(toStablecoin).approve(
                univ2Router,
                IERC20(toStablecoin).balanceOf(address(this))
            );
        } else {
            USDT(toStablecoin).approve(
                univ2Router,
                IERC20(toStablecoin).balanceOf(address(this))
            );
        }

        (, , uint256 liquidity) = IUniswapRouterV2(univ2Router).addLiquidity(
            weth,
            toStablecoin,
            IERC20(weth).balanceOf(address(this)),
            IERC20(toStablecoin).balanceOf(address(this)),
            0,
            0,
            msg.sender,
            now + 60
        );

        // Refund excess tokens
        IERC20(weth).transfer(
            _refundExcess,
            IERC20(weth).balanceOf(address(this))
        );

        if (toStablecoin != usdt) {
            IERC20(toStablecoin).transfer(
                _refundExcess,
                IERC20(toStablecoin).balanceOf(address(this))
            );
        } else {
            USDT(toStablecoin).transfer(
                _refundExcess,
                IERC20(toStablecoin).balanceOf(address(this))
            );
        }

        return liquidity;
    }

    function _getIndex(address stablecoin) internal pure returns (int128) {
        if (stablecoin == dai) {
            return 0;
        }

        if (stablecoin == usdc) {
            return 1;
        }

        if (stablecoin == usdt) {
            return 2;
        }

        if (stablecoin == susd) {
            return 3;
        }

        revert("!index");
    }

    function _getPath(address stablecoin)
        internal
        pure
        returns (address[] memory)
    {
        address[] memory path = new address[](2);
        path[0] = stablecoin;
        path[1] = weth;

        return path;
    }
}
