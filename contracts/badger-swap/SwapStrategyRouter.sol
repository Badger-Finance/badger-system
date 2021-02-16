// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";

import "interfaces/badger/ISwapStrategyRouter.sol";

contract SwapStrategyRouter is ISwapStrategyRouter, AccessControlUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    // Swapper strategy IDs.
    EnumerableSetUpgradeable.AddressSet private strategies;

    function initialize(address _admin) public initializer {
        __AccessControl_init();
        __ReentrancyGuard_init();

        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
    }

    // Return the optimal rate and the strategy ID.
    // No access restriction since this fn is stateless.
    function optimizeSwap(
        address _from,
        address _to,
        uint256 _amount
    ) external override nonReentrant returns (address strategy, uint256 amount) {
        require(strategies.length() > 0, "no registered strategies");

        uint256 _optimalAmount;
        address _optimalStrategy;
        for (uint256 i = 0; i < strategies.length(); i++) {
            address _strategy = strategies.at(i);
            uint256 _swapAmount = ISwapStrategy(_strategy).estimateSwapAmount(_from, _to, _amount);
            if (_swapAmount > _optimalAmount) {
                _optimalAmount = _swapAmount;
                _optimalStrategy = _strategy;
            }
        }
        return (_optimalStrategy, _optimalAmount);
    }

    /* ========== ADMIN ========== */
    function addSwapStrategy(address _strategy) external onlyAdmin {
        strategies.add(_strategy);
    }

    /* ========== MODIFIERS ========== */
    modifier onlyAdmin {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
        _;
    }
}
