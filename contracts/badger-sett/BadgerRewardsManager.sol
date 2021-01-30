// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "contracts/badger-sett/strategies/Swapper.sol";

contract BadgerRewardsManager is AccessControlUpgradeable, ReentrancyGuardUpgradeable, PausableUpgradeable, Swapper {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    mapping (address => bool) public isApprovedStrategy;

    event ApproveStrategy(address recipient);
    event RevokeStrategy(address recipient);
    event Call(address to, uint256 value, bytes data);
    
    bytes32 public constant SWAPPER_ROLE = keccak256("SWAPPER_ROLE");
    bytes32 public constant DISTRIBUTOR_ROLE = keccak256("DISTRIBUTOR_ROLE");
    bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    function initialize(address admin, address initialDistributor, address initialSwapper, address initialPauser, address initialUnpauser) public initializer {
        __AccessControl_init();
        __Pausable_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, admin);
        _setupRole(DISTRIBUTOR_ROLE, initialDistributor);
        _setupRole(KEEPER_ROLE, initialDistributor); // Defaults as distributor
        _setupRole(SWAPPER_ROLE, initialSwapper);
        _setupRole(PAUSER_ROLE, initialPauser);
        _setupRole(UNPAUSER_ROLE, initialUnpauser);
    }

    /// ===== Modifiers =====

    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyPauser() internal view {
        require(hasRole(PAUSER_ROLE, msg.sender), "onlyPauser");
    }

    function _onlyUnpauser() internal view {
        require(hasRole(UNPAUSER_ROLE, msg.sender), "onlyUnpauser");
    }

    function _onlyDistributor() internal view {
        require(hasRole(DISTRIBUTOR_ROLE, msg.sender), "DISTRIBUTOR_ROLE");
    }

    function _onlyKeeper() internal view {
        require(hasRole(KEEPER_ROLE, msg.sender), "KEEPER_ROLE");
    }

    function _onlySwapper() internal view {
        require(hasRole(SWAPPER_ROLE, msg.sender), "SWAPPER_ROLE");
    }

    function _onlyApprovedStrategies(address recipient) internal view {
        require(isApprovedStrategy[recipient] == true, "strategy strategy not approved");
    }

    /// ===== Permissioned Functions: Admin =====
    function approveStrategy(address recipient) external {
        _onlyAdmin();
        isApprovedStrategy[recipient] = true;
        emit ApproveStrategy(recipient);
    }

    function revokeStrategy(address recipient) external {
        _onlyAdmin();
        isApprovedStrategy[recipient] = false;
        emit RevokeStrategy(recipient);
    }

    /// @notice Pause publishing of new roots
    function pause() external {
        _onlyPauser();
        _pause();
    }

    /// @notice Unpause publishing of new roots
    function unpause() external {
        _onlyUnpauser();
        _unpause();
    }

    // ===== Permissioned Functions: Distributor =====
    function transferWant(address want, address strategy, uint256 amount) external {
        _onlyDistributor();
        _onlyApprovedStrategies(strategy);
        
        require(IStrategy(strategy).want() == want, "Incorrect want for strategy");

        require(IERC20Upgradeable(want).transfer(strategy, amount), "Want transfer failed");

        // Atomically add to strategy positions
        IStrategy(strategy).deposit();
    }

    // ===== Permissioned Functions: Keeper =====
    function deposit(address strategy) external {
        _onlyKeeper();
        _onlyApprovedStrategies(strategy);
        
        IStrategy(strategy).deposit();
    }

    function tend(address strategy) external {
        _onlyKeeper();
        _onlyApprovedStrategies(strategy);
        
        IStrategy(strategy).tend();
    }

    function harvest(address strategy) external {
        _onlyKeeper();
        _onlyApprovedStrategies(strategy);

        IStrategy(strategy).harvest();
    }

    // ===== Permissioned Functions: Swapper =====
    function swapExactTokensForTokensUniswap(address token0, uint256 amount, address[] memory path) external {
        _onlySwapper();
        _swap_uniswap(token0, amount, path);
    }
    function swapExactTokensForTokensSushiswap(address token0, uint256 amount, address[] memory path) external {
        _onlySwapper();
        _swap_sushiswap(token0, amount, path);
    }

    function addLiquidityUniswap(address token0, address token1) external {
        _onlySwapper();
        _add_max_liquidity_uniswap(token0, token1);
    }
    function addLiquiditySushiswap(address token0, address token1) external {
        _onlySwapper();
        _add_max_liquidity_sushiswap(token0, token1);
    }
}
