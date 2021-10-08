// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveExchange.sol";
import "interfaces/curve/ICurveRegistry.sol";
import "./BaseSwapper.sol";

/*
    Expands swapping functionality over base strategy
    - ETH in and ETH out Variants
    - Sushiswap support in addition to Uniswap
*/
contract CurveSwapper is BaseSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public constant addressProvider = 0x0000000022D53366457F9d5E68Ec105046FC4383;

    uint256 public constant registryId = 0;
    uint256 public constant metaPoolFactoryId = 3;

    function _exchange(
        address _from,
        address _to,
        uint256 _dx,
        uint256 _min_dy,
        uint256 _index,
        bool _isFactoryPool
    ) internal {
        address poolRegistry = ICurveRegistryAddressProvider(addressProvider).get_address(_isFactoryPool ? metaPoolFactoryId : registryId);
        address poolAddress = ICurveRegistry(poolRegistry).find_pool_for_coins(_from, _to, _index);

        if (poolAddress != address(0)) {
            _safeApproveHelper(_from, poolAddress, _dx);
            (int128 i, int128 j, ) = ICurveRegistry(poolRegistry).get_coin_indices(poolAddress, _from, _to);
            ICurveFi(poolAddress).exchange(i, j, _dx, _min_dy);
        }
    }

    function _add_liquidity_single_coin(
        address swap,
        address pool,
        address inputToken,
        uint256 inputAmount,
        uint256 inputPosition,
        uint256 numPoolElements,
        uint256 min_mint_amount
    ) internal {
        _safeApproveHelper(inputToken, swap, inputAmount);
        if (numPoolElements == 2) {
            uint256[2] memory convertedAmounts;
            convertedAmounts[inputPosition] = inputAmount;
            ICurveFi(swap).add_liquidity(convertedAmounts, min_mint_amount);
        } else if (numPoolElements == 3) {
            uint256[3] memory convertedAmounts;
            convertedAmounts[inputPosition] = inputAmount;
            ICurveFi(swap).add_liquidity(convertedAmounts, min_mint_amount);
        } else if (numPoolElements == 4) {
            uint256[4] memory convertedAmounts;
            convertedAmounts[inputPosition] = inputAmount;
            ICurveFi(swap).add_liquidity(convertedAmounts, min_mint_amount);
        } else {
            revert("Bad numPoolElements");
        }
    }

    function _add_liquidity(
        address pool,
        uint256[2] memory amounts,
        uint256 min_mint_amount
    ) internal {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function _add_liquidity(
        address pool,
        uint256[3] memory amounts,
        uint256 min_mint_amount
    ) internal {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function _add_liquidity(
        address pool,
        uint256[4] memory amounts,
        uint256 min_mint_amount
    ) internal {
        ICurveFi(pool).add_liquidity(amounts, min_mint_amount);
    }

    function _remove_liquidity_one_coin(
        address swap,
        uint256 _token_amount,
        int128 i,
        uint256 _min_amount
    ) internal {
        ICurveFi(swap).remove_liquidity_one_coin(_token_amount, i, _min_amount);
    }
}
