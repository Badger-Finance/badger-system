// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/curve/ICurveFi.sol";
/*
    Expands swapping functionality over base strategy
    - ETH in and ETH out Variants
    - Sushiswap support in addition to Uniswap
*/
contract CurveLibraryExternal {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    bytes32 public constant UNI_V2_LIKE_ROUTER_ROLE = keccak256("UNI_LIKE_ROUTER_ROLE");
    uint256 public constant MAX_FEE = 10000;
    
    IBadgerAccessControl public constant badgerAccessControl = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address public constant uniswap = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap router
    address public constant sushiswap = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F; // Sushiswap router

    function add_liquidity(
        address pool,
        uint256[2] memory amounts,
        uint256 min_mint_amount
    ) public {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function add_liquidity(
        address pool,
        uint256[3] memory amounts,
        uint256 min_mint_amount
    ) public {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function add_liquidity(
        address pool,
        uint256[4] memory amounts,
        uint256 min_mint_amount
    ) public {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function remove_liquidity_one_coin(
        address pool,
        uint256 _token_amount,
        int128 i,
        uint256 _min_amount
    ) public {
        ICurveFi(pool).remove_liquidity_one_coin(_token_amount, i, _min_amount);
    }
}
