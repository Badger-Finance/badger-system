// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";

import "interfaces/curve/ICurveExchange.sol";
import "interfaces/badger/ISwapStrategyRouter.sol";

contract CurveSwapStrategy is AccessControlUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    // Only swapper is allowed to make swaps.
    bytes32 public constant SWAPPER_ROLE = keccak256("SWAPPER_ROLE");
    // The curve exchange contract is registered in the address provider with ID 2.
    uint256 public constant CURVE_REGISTRY_EXCHANGE_ID = 2;

    address public curveRegistryAddressProvider;

    function initialize(address _admin, address _registry) public initializer {
        __AccessControl_init();
        __ReentrancyGuard_init();

        require(_admin != address(0x0), "must set admin address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);

        require(_registry != address(0x0), "must set registry address provider address");
        curveRegistryAddressProvider = _registry;
    }

    function swapTokens(
        address _from,
        address _to,
        uint256 _amount,
        uint256 _slippage
    ) external nonReentrant onlySwapper returns (uint256 amount) {
        (address registry, address pool, uint256 exchangeAmount) = _estimateSwapAmount(_from, _to, _amount);

        _slippage = uint256(1e4).sub(_slippage);
        uint256 minAmount = _amount.mul(_slippage).div(1e4);
        require(exchangeAmount > minAmount, "slippage too high");

        _approveBalance(_from, registry, _amount);
        // msg.sender must supply from token for _amount.
        IERC20Upgradeable(_from).safeTransferFrom(msg.sender, address(this), _amount);
        amount = ICurveRegistryExchange(registry).exchange(
            pool,
            _from,
            _to,
            _amount,
            minAmount,
            // Swap strategy caller is the receiver of the swap.
            msg.sender
        );
        require(amount > minAmount, "swapped amount less than min amount");

        return amount;
    }

    // Anyone can estimate swap amount as this fn is stateless.
    function estimateSwapAmount(
        address _from,
        address _to,
        uint256 _amount
    ) external nonReentrant returns (uint256) {
        (address _, address __, uint256 amount) = _estimateSwapAmount(_from, _to, _amount);
        return amount;
    }

    function _estimateSwapAmount(
        address _from,
        address _to,
        uint256 _amount
    )
        internal
        returns (
            address registry,
            address pool,
            uint256 amount
        )
    {
        // NB: Pulling the registry exchange address w/in the tx because
        // it seemed like this could change over time according to the docs.
        registry = ICurveRegistryAddressProvider(curveRegistryAddressProvider).get_address(CURVE_REGISTRY_EXCHANGE_ID);
        (pool, amount) = ICurveRegistryExchange(registry).get_best_rate(_from, _to, _amount);
        return (registry, pool, amount);
    }

    function _approveBalance(
        address _token,
        address _spender,
        uint256 _amount
    ) internal {
        if (IERC20Upgradeable(_token).allowance(address(this), _spender) < _amount) {
            // Approve max spend.
            IERC20Upgradeable(_token).approve(_spender, (1 << 64) - 1);
        }
    }

    /* ========== ADMIN ========== */
    function setRegistryAddressProvider(address _registry) external onlyAdmin {
        curveRegistryAddressProvider = _registry;
    }

    /* ========== MODIFIERS ========== */
    modifier onlyAdmin {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
        _;
    }

    modifier onlySwapper {
        require(hasRole(SWAPPER_ROLE, msg.sender), "onlySwapper");
        _;
    }
}
