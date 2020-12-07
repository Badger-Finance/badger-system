// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

import "../../interfaces/badger/IController.sol";
import "../../interfaces/erc20/IERC20Detailed.sol";
import "./SettAccessControlDefended.sol";

/* 
    Source: https://github.com/iearn-finance/yearn-protocol/blob/develop/contracts/vaults/yVault.sol
*/
contract Sett is ERC20Upgradeable, SettAccessControlDefended {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    IERC20Upgradeable public token;

    uint256 public min;
    uint256 public constant max = 10000;

    address public controller;

    mapping(address => uint256) public blockLock;

    string internal constant _defaultNamePrefix = "Badger Sett ";
    string internal constant _symbolSymbolPrefix = "b";

    event FullPricePerShareUpdated(uint256 value, uint256 indexed timestamp, uint256 indexed blockNumber);

    function initialize(
        address _token,
        address _controller,
        address _governance,
        address _keeper,
        bool _overrideTokenName,
        string memory _namePrefix,
        string memory _symbolPrefix
    ) public initializer {
        IERC20Detailed namedToken = IERC20Detailed(_token);
        string memory tokenName = namedToken.name();
        string memory tokenSymbol = namedToken.symbol();

        string memory name;
        string memory symbol;

        if (_overrideTokenName) {
            name = string(abi.encodePacked(_namePrefix, tokenName));
            symbol = string(abi.encodePacked(_symbolPrefix, tokenSymbol));
        } else {
            name = string(abi.encodePacked(_defaultNamePrefix, tokenName));
            symbol = string(abi.encodePacked(_symbolSymbolPrefix, tokenSymbol));
        }

        __ERC20_init(name, symbol);

        token = IERC20Upgradeable(_token);
        governance = _governance;
        strategist = address(0);
        keeper = _keeper;
        controller = _controller;

        min = 9500;

        emit FullPricePerShareUpdated(getPricePerFullShare(), now, block.number);
    }

    /// ===== Modifiers =====

    function _onlyController() internal view {
        require(msg.sender == controller, "onlyController");
    }

    function _blockLocked() internal view {
        require(blockLock[msg.sender] < block.number, "blockLocked");
    }

    /// ===== View Functions =====

    function getPricePerFullShare() public view returns (uint256) {
        if (totalSupply() == 0) {
            return 1e18;
        }
        return balance().mul(1e18).div(totalSupply());
    }

    /// @notice Return the total balance of the underlying token within the system
    /// @notice Sums the balance in the Sett, the Controller, and the Strategy
    function balance() public view returns (uint256) {
        return token.balanceOf(address(this)).add(IController(controller).balanceOf(address(token)));
    }

    /// @notice Defines how much of the Setts' underlying can be borrowed by the Strategy for use
    /// @notice Custom logic in here for how much the vault allows to be borrowed
    /// @notice Sets minimum required on-hand to keep small withdrawals cheap
    function available() public view returns (uint256) {
        return token.balanceOf(address(this)).mul(min).div(max);
    }

    /// ===== Public Actions =====

    /// @notice Deposit assets into the Sett, and return corresponding shares to the user
    /// @notice Only callable by EOA accounts that pass the _defend() check
    function deposit(uint256 _amount) public {
        _defend();
        _blockLocked();

        _lockForBlock(msg.sender);
        _deposit(_amount);
    }

    /// @notice Convenience function: Deposit entire balance of asset into the Sett, and return corresponding shares to the user
    /// @notice Only callable by EOA accounts that pass the _defend() check
    function depositAll() external {
        _defend();
        _blockLocked();

        _lockForBlock(msg.sender);
        _deposit(token.balanceOf(msg.sender));
    }

    /// @notice No rebalance implementation for lower fees and faster swaps
    function withdraw(uint256 _shares) public {
        _defend();
        _blockLocked();

        _lockForBlock(msg.sender);
        _withdraw(_shares);
    }

    /// @notice Convenience function: Withdraw all shares of the sender
    function withdrawAll() external {
        _defend();
        _blockLocked();

        _lockForBlock(msg.sender);
        _withdraw(balanceOf(msg.sender));
    }

    /// ===== Permissioned Actions: Governance =====

    /// @notice Set minimum threshold of underlying that must be deposited in strategy
    /// @notice Can only be changed by governance
    function setMin(uint256 _min) external {
        _onlyGovernance();
        min = _min;
    }

    /// @notice Change controller address
    /// @notice Can only be changed by governance
    function setController(address _controller) public {
        _onlyGovernance();
        controller = _controller;
    }

    /// ===== Permissioned Actions: Controller =====

    /// @notice Used to swap any borrowed reserve over the debt limit to liquidate to 'token'
    /// @notice Only controller can trigger harvests
    function harvest(address reserve, uint256 amount) external {
        _onlyController();
        require(reserve != address(token), "token");
        IERC20Upgradeable(reserve).safeTransfer(controller, amount);
    }

    /// ===== Permissioned Functions: Trusted Actors =====

    /// @notice Transfer the underlying available to be claimed to the controller
    /// @notice The controller will deposit into the Strategy for yield-generating activities
    /// @notice Permissionless operation
    function earn() public {
        _onlyAuthorizedActors();

        uint256 _bal = available();
        token.safeTransfer(controller, _bal);
        IController(controller).earn(address(token), _bal);
    }

    /// @dev Emit event tracking current full price per share
    /// @dev Provides a pure on-chain way of approximating APY
    function trackFullPricePerShare() external {
        _onlyAuthorizedActors();
        emit FullPricePerShareUpdated(getPricePerFullShare(), now, block.number);
    }

    /// ===== Internal Implementations =====

    /// @dev Calculate the number of shares to issue for a given deposit
    /// @dev This is based on the realized value of underlying assets between Sett & associated Strategy
    function _deposit(uint256 _amount) internal {
        uint256 _pool = balance();
        uint256 _before = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), _amount);
        uint256 _after = token.balanceOf(address(this));
        _amount = _after.sub(_before); // Additional check for deflationary tokens
        uint256 shares = 0;
        if (totalSupply() == 0) {
            shares = _amount;
        } else {
            shares = (_amount.mul(totalSupply())).div(_pool);
        }
        _mint(msg.sender, shares);
    }

    // No rebalance implementation for lower fees and faster swaps
    function _withdraw(uint256 _shares) internal {
        uint256 r = (balance().mul(_shares)).div(totalSupply());
        _burn(msg.sender, _shares);

        // Check balance
        uint256 b = token.balanceOf(address(this));
        if (b < r) {
            uint256 _toWithdraw = r.sub(b);
            IController(controller).withdraw(address(token), _toWithdraw);
            uint256 _after = token.balanceOf(address(this));
            uint256 _diff = _after.sub(b);
            if (_diff < _toWithdraw) {
                r = b.add(_diff);
            }
        }

        token.safeTransfer(msg.sender, r);
    }

    function _lockForBlock(address account) internal {
        blockLock[account] = block.number;
    }

    /// ===== ERC20 Overrides =====

    /// @dev Add blockLock to transfers, users cannot transfer tokens in the same block as a deposit or withdrawal.
    function transfer(address recipient, uint256 amount) public virtual override returns (bool) {
        _blockLocked();
        return super.transfer(recipient, amount);
    }

    function transferFrom(
        address sender,
        address recipient,
        uint256 amount
    ) public virtual override returns (bool) {
        _blockLocked();
        return super.transferFrom(sender, recipient, amount);
    }
}
