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
    - pancakeswap support in addition to Uniswap
*/
abstract contract PancakeSwapper is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant pancakeswap = 0x05fF2B0DB69458A0750badebc4f9e13aDd608C7F; // Pancake router

    /// @notice Swap specified balance of given token on Uniswap with given path
    function _swap_pancakeswap(
        address startToken,
        uint256 balance,
        address[] memory path
    ) internal {
        _safeApproveHelper(startToken, pancakeswap, balance);
        IUniswapRouterV2(pancakeswap).swapExactTokensForTokens(balance, 0, path, address(this), now);
    }

    function _get_pancake_pair(address token0, address token1) internal view returns (address) { 
        address factory = IUniswapRouterV2(pancakeswap).factory();
        return IUniswapV2Factory(factory).getPair(token0, token1);
    }

    /// @notice Add liquidity to uniswap for specified token pair, utilizing the maximum balance possible
    function _add_max_liquidity_pancakeswap(address token0, address token1) internal {
        uint256 _token0Balance = IERC20Upgradeable(token0).balanceOf(address(this));
        uint256 _token1Balance = IERC20Upgradeable(token1).balanceOf(address(this));
        
        if (_token0Balance > 0 && _token1Balance > 0) {
            _safeApproveHelper(token0, pancakeswap, _token0Balance);
            _safeApproveHelper(token1, pancakeswap, _token1Balance);

            IUniswapRouterV2(pancakeswap).addLiquidity(token0, token1, _token0Balance, _token1Balance, 0, 0, address(this), block.timestamp);
        }
    }

    uint256[50] private __gap;
}
