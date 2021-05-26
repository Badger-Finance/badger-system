pragma solidity 0.6.6;

import {ERC20Upgradeable} from "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import {AccessControlUpgradeable} from "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract UpgradeableMetaToken is ERC20Upgradeable, AccessControlUpgradeable {
    bytes32 public constant DEPOSITOR_ROLE = keccak256("DEPOSITOR_ROLE");

    function initialize(
        string calldata _name,
        string calldata _symbol,
        uint8 _decimals
    ) external initializer {
        __AccessControl_init();
        __ERC20_init(_name, _symbol);
        _setupDecimals(_decimals);

        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @notice called when token is deposited on root chain
     * @dev only callable by approved/integrated bridge token contracts
     * @param _to user depositing tokens
     * @param _amount amount of tokens to deposit
     */
    function deposit(address _to, uint256 _amount) external onlyDepositer {
        _mint(_to, _amount);
    }

    /**
     * @notice called when user wants to withdraw tokens back to root chain
     * @dev only callable by approved/integrated bridge token contracts
     * @param _from user withdrawing tokens
     * @param _amount amount of tokens to withdraw
     */
    function withdraw(address _from, uint256 _amount) external onlyDepositer {
        _burn(_from, _amount);
    }

    /* ========== MODIFIERS ========== */
    modifier onlyDepositer {
        require(hasRole(DEPOSITOR_ROLE, msg.sender), "only depositor");
        _;
    }
}
