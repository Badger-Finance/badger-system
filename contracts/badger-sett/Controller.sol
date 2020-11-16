// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

import "interfaces/badger/IConverter.sol";
import "interfaces/badger/IOneSplitAudit.sol";
import "interfaces/badger/IStrategy.sol";

contract Controller is Initializable {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public governance;
    address public strategist;

    address public onesplit;
    address public rewards;
    mapping(address => address) public vaults;
    mapping(address => address) public strategies;
    mapping(address => mapping(address => address)) public converters;

    mapping(address => mapping(address => bool)) public approvedStrategies;

    uint256 public split = 500;
    uint256 public constant max = 10000;

    function initialize(
        address _governance,
        address _strategist,
        address _rewards
    ) public initializer {
        governance = _governance;
        strategist = _strategist;
        rewards = _rewards;

        onesplit = address(0x50FDA034C0Ce7a8f7EFDAebDA7Aa7cA21CC1267e);
    }

    function _onlyGovernance() internal view {
        require(msg.sender == governance, "!governance");
    }

    function _onlyGovernanceOrStrategist() internal view {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");
    }

    function setRewards(address _rewards) public {
        _onlyGovernance();
        rewards = _rewards;
    }

    function setStrategist(address _strategist) public {
        _onlyGovernance();
        strategist = _strategist;
    }

    function setSplit(uint256 _split) public {
        _onlyGovernance();
        split = _split;
    }

    function setOneSplit(address _onesplit) public {
        _onlyGovernance();
        onesplit = _onesplit;
    }

    function setGovernance(address _governance) public {
        _onlyGovernance();
        governance = _governance;
    }

    function setVault(address _token, address _vault) public {
        _onlyGovernanceOrStrategist();
        require(vaults[_token] == address(0), "vault");
        vaults[_token] = _vault;
    }

    function approveStrategy(address _token, address _strategy) public {
        _onlyGovernance();
        approvedStrategies[_token][_strategy] = true;
    }

    function revokeStrategy(address _token, address _strategy) public {
        _onlyGovernance();
        approvedStrategies[_token][_strategy] = false;
    }

    function setConverter(
        address _input,
        address _output,
        address _converter
    ) public {
        _onlyGovernanceOrStrategist();
        converters[_input][_output] = _converter;
    }

    /// @notice Migrate assets from existing strategy to a new strategy.
    /// @notice The new strategy must have been previously approved by governance.
    /// @notice Strategist or governance can freely switch between approved strategies
    function setStrategy(address _token, address _strategy) public {
        _onlyGovernanceOrStrategist();
        require(approvedStrategies[_token][_strategy] == true, "!approved");

        address _current = strategies[_token];
        if (_current != address(0)) {
            IStrategy(_current).withdrawAll();
        }
        strategies[_token] = _strategy;
    }

    /// @notice Deposit given token to strategy, converting it to the strategies' want first (if required).
    /// @param _token Token to deposit (will be converted to want by converter). If no converter is registered, the transaction will revert.
    /// @param _amount Amount of token to deposit
    function earn(address _token, uint256 _amount) public {
        address _strategy = strategies[_token];
        address _want = IStrategy(_strategy).want();
        if (_want != _token) {
            address converter = converters[_token][_want];
            IERC20Upgradeable(_token).safeTransfer(converter, _amount);
            _amount = IConverter(converter).convert(_strategy);
            IERC20Upgradeable(_want).safeTransfer(_strategy, _amount);
        } else {
            IERC20Upgradeable(_token).safeTransfer(_strategy, _amount);
        }
        IStrategy(_strategy).deposit();
    }

    /// @notice Get the balance of the given tokens' current strategy of that token.
    function balanceOf(address _token) external view returns (uint256) {
        return IStrategy(strategies[_token]).balanceOf();
    }

    /// @notice Withdraw the entire balance of a token from that tokens' current strategy.
    /// @notice Does not trigger a withdrawal fee.
    /// @notice Entire balance will be sent to corresponding Sett.
    function withdrawAll(address _token) public {
        _onlyGovernanceOrStrategist();
        IStrategy(strategies[_token]).withdrawAll();
    }

    /// @dev Transfer an amount of the specified token from the controller to the sender.
    /// @dev Token balance are never meant to exist in the controller, this is purely a safeguard.
    function inCaseTokensGetStuck(address _token, uint256 _amount) public {
        _onlyGovernanceOrStrategist();
        IERC20Upgradeable(_token).safeTransfer(msg.sender, _amount);
    }

    /// @dev Transfer an amount of the specified token from the controller to the sender.
    /// @dev Token balance are never meant to exist in the controller, this is purely a safeguard.
    function inCaseStrategyTokenGetStuck(address _strategy, address _token) public {
        _onlyGovernanceOrStrategist();
        IStrategy(_strategy).withdrawOther(_token);
    }

    function getExpectedReturn(
        address _strategy,
        address _token,
        uint256 parts
    ) public view returns (uint256 expected) {
        uint256 _balance = IERC20Upgradeable(_token).balanceOf(_strategy);
        address _want = IStrategy(_strategy).want();
        (expected, ) = IOneSplitAudit(onesplit).getExpectedReturn(_token, _want, _balance, parts, 0);
    }

    /// @notice Gather yield of non-core strategy tokens
    /// @dev Only allows to withdraw non-core strategy tokens ~ this is over and above normal yield
    function yearn(
        address _strategy,
        address _token,
        uint256 parts
    ) public {
        _onlyGovernanceOrStrategist();
        // This contract should never have value in it, but just incase since this is a public call
        uint256 _before = IERC20Upgradeable(_token).balanceOf(address(this));
        IStrategy(_strategy).withdrawOther(_token);
        uint256 _after = IERC20Upgradeable(_token).balanceOf(address(this));
        if (_after > _before) {
            uint256 _amount = _after.sub(_before);
            address _want = IStrategy(_strategy).want();
            uint256[] memory _distribution;
            uint256 _expected;
            _before = IERC20Upgradeable(_want).balanceOf(address(this));
            IERC20Upgradeable(_token).safeApprove(onesplit, 0);
            IERC20Upgradeable(_token).safeApprove(onesplit, _amount);
            (_expected, _distribution) = IOneSplitAudit(onesplit).getExpectedReturn(_token, _want, _amount, parts, 0);
            IOneSplitAudit(onesplit).swap(_token, _want, _amount, _expected, _distribution, 0);
            _after = IERC20Upgradeable(_want).balanceOf(address(this));
            if (_after > _before) {
                _amount = _after.sub(_before);
                uint256 _reward = _amount.mul(split).div(max);
                earn(_want, _amount.sub(_reward));
                IERC20Upgradeable(_want).safeTransfer(rewards, _reward);
            }
        }
    }

    /// @notice Wtihdraw a given token from it's corresponding strategy
    /// @notice Only the associated vault can call, in response to a user withdrawal request
    function withdraw(address _token, uint256 _amount) public {
        require(msg.sender == vaults[_token], "!vault");
        IStrategy(strategies[_token]).withdraw(_amount);
    }
}
