// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapV2Factory.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IStrategy.sol";

import "../SettAccessControl.sol";
import "./BaseStrategy.sol";

/*
    Expands swapping functionality over base strategy
    - ETH in and ETH out Variants
    - Sushiswap support in addition to Uniswap
*/
abstract contract Swapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant uniswap = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Router
    address public constant sushiswap = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F; // Sushiswap router
    uint256 public constant MAX_FEE = 10000;

    /// @notice Swap specified balance of given token on Uniswap with given path
    function _swap_uniswap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, uniswap, balance);
        IUniswapRouterV2(uniswap).swapExactTokensForTokens(balance, 0, path, address(this), now);
    }

    /// @notice Swap specified balance of given token on Uniswap with given path
    function _swap_sushiswap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, sushiswap, balance);
        IUniswapRouterV2(sushiswap).swapExactTokensForTokens(balance, 0, path, address(this), now);
    }

    function _swapEthIn_uniswap(uint256 balance, address[] memory path) internal {
        IUniswapRouterV2(uniswap).swapExactETHForTokens{value: balance}(0, path, address(this), now);
    }

    function _swapEthIn_sushiswap(uint256 balance, address[] memory path) internal {
        IUniswapRouterV2(sushiswap).swapExactETHForTokens{value: balance}(0, path, address(this), now);
    }

    function _swapEthOut_uniswap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, uniswap, balance);
        IUniswapRouterV2(uniswap).swapExactTokensForETH(balance, 0, path, address(this), now);
    }

    function _swapEthOut_sushiswap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, sushiswap, balance);
        IUniswapRouterV2(sushiswap).swapExactTokensForETH(balance, 0, path, address(this), now);
    }

    function _get_uni_pair(address token0, address token1) internal view returns (address) {
        address factory = IUniswapRouterV2(uniswap).factory();
        return IUniswapV2Factory(factory).getPair(token0, token1);
    }

    function _get_sushi_pair(address token0, address token1) internal view returns (address) {
        address factory = IUniswapRouterV2(sushiswap).factory();
        return IUniswapV2Factory(factory).getPair(token0, token1);
    }

    /// @notice Add liquidity to uniswap for specified token pair, utilizing the maximum balance possible
    function _add_max_liquidity_sushiswap(address token0, address token1) internal {
        uint256 _token0Balance = IERC20Upgradeable(token0).balanceOf(address(this));
        uint256 _token1Balance = IERC20Upgradeable(token1).balanceOf(address(this));

        _safeApproveHelper(token0, sushiswap, _token0Balance);
        _safeApproveHelper(token1, sushiswap, _token1Balance);

        IUniswapRouterV2(sushiswap).addLiquidity(token0, token1, _token0Balance, _token1Balance, 0, 0, address(this), block.timestamp);
    }

    function _processFee(
        address token,
        uint256 amount,
        uint256 feeBps,
        address recipient
    ) internal returns (uint256) {
        if (feeBps == 0) {
            return 0;
        }
        uint256 fee = amount.mul(feeBps).div(MAX_FEE);
        IERC20Upgradeable(token).safeTransfer(recipient, fee);
        return fee;
    }

    /// @dev Reset approval and approve exact amount
    function _safeApproveHelper(
        address token,
        address recipient,
        uint256 amount
    ) internal {
        IERC20Upgradeable(token).safeApprove(recipient, 0);
        IERC20Upgradeable(token).safeApprove(recipient, amount);
    }

    /// @notice Swap specified balance of given token on Uniswap with given path
    function _swap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, uniswap, balance);
        IUniswapRouterV2(uniswap).swapExactTokensForTokens(balance, 0, path, address(this), now);
    }

    function _swapEthIn(uint256 balance, address[] memory path) internal {
        IUniswapRouterV2(uniswap).swapExactETHForTokens{value: balance}(0, path, address(this), now);
    }

    function _swapEthOut(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, uniswap, balance);
        IUniswapRouterV2(uniswap).swapExactTokensForETH(balance, 0, path, address(this), now);
    }

    /// @notice Add liquidity to uniswap for specified token pair, utilizing the maximum balance possible
    function _add_max_liquidity_uniswap(address token0, address token1) internal virtual {
        uint256 _token0Balance = IERC20Upgradeable(token0).balanceOf(address(this));
        uint256 _token1Balance = IERC20Upgradeable(token1).balanceOf(address(this));

        _safeApproveHelper(token0, uniswap, _token0Balance);
        _safeApproveHelper(token1, uniswap, _token1Balance);

        IUniswapRouterV2(uniswap).addLiquidity(token0, token1, _token0Balance, _token1Balance, 0, 0, address(this), block.timestamp);
    }

    /// @notice Utility function to diff two numbers, expects higher value in first position
    function _diff(uint256 a, uint256 b) internal pure returns (uint256) {
        require(a >= b, "diff/expected-higher-number-in-first-position");
        return a.sub(b);
    }

    uint256[50] private __gap;
}
