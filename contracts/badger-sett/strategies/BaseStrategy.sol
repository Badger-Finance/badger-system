// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IController.sol";
import "interfaces/badger/IStrategy.sol";

abstract contract BaseStrategy is Initializable {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    event Deposit(uint256 amount, address location);
    event Withdraw(uint256 amount);
    event WithdrawAll(uint256 balance);
    event WithdrawOther(address token, uint256 amount);
    event SetStrategist(address strategist);
    event SetGovernance(address governance);
    event SetController(address controller);
    event SetWithdrawalFee(uint256 withdrawalFee);
    event SetPerformanceFeeStrategist(uint256 performanceFeeStrategist);
    event SetPerformanceFeeGovernance(uint256 performanceFeeGovernance);

    address public want; // Want: Curve.fi renBTC/wBTC (crvRenWBTC) LP token

    uint256 public performanceFeeGovernance;
    uint256 public performanceFeeStrategist;
    uint256 public withdrawalFee;

    uint256 public constant MAX_FEE = 10000;

    address public governance;
    address public controller;
    address public strategist;

    function _onlyController() internal view {
        require(msg.sender == controller, "!controller");
    }

    function _onlyGovernance() internal view {
        require(msg.sender == governance, "!governance");
    }

    function _onlyGovernanceOrStrategist() internal view {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");
    }

    function setStrategist(address _strategist) external {
        _onlyGovernance();
        strategist = _strategist;
    }

    function setWithdrawalFee(uint256 _withdrawalFee) external {
        _onlyGovernance();
        withdrawalFee = _withdrawalFee;
    }

    function setPerformanceFeeStrategist(uint256 _performanceFeeStrategist) external {
        _onlyGovernance();
        performanceFeeStrategist = _performanceFeeStrategist;
    }

    function setPerformanceFeeGovernance(uint256 _performanceFeeGovernance) external {
        _onlyGovernance();
        performanceFeeGovernance = _performanceFeeGovernance;
    }

    function setGovernance(address _governance) external {
        _onlyGovernance();
        governance = _governance;
    }

    function setController(address _controller) external {
        _onlyGovernance();
        controller = _controller;
    }

    function _processStrategistPerformanceFee(uint256 _amount) internal returns (uint256) {
        uint256 fee = _amount.mul(performanceFeeStrategist).div(MAX_FEE);
        IERC20Upgradeable(want).safeTransfer(strategist, fee);
        return fee;
    }

    function _processGovernancePerformanceFee(uint256 _amount) internal returns (uint256) {
        uint256 fee = _amount.mul(performanceFeeGovernance).div(MAX_FEE);
        IERC20Upgradeable(want).safeTransfer(IController(controller).rewards(), fee);
        return fee;
    }

    function _processWithdrawalFee(uint256 _amount) internal returns (uint256) {
        uint256 fee = _amount.mul(withdrawalFee).div(MAX_FEE);
        IERC20Upgradeable(want).safeTransfer(IController(controller).rewards(), fee);
        return fee;
    }

    function _transferToVault(uint256 _amount) internal {
        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds
        IERC20Upgradeable(want).safeTransfer(_vault, _amount);
    }

    function deposit() external virtual;

    function harvest() external virtual;

    function getName() external pure virtual returns (string memory);

    // Controller | Vault role - withdraw should always return to Vault
    function withdraw(uint256) external virtual;

    // Controller | Vault role - withdraw should always return to Vault
    function withdrawAll() external virtual returns (uint256);

    function balanceOf() public view virtual returns (uint256);

    // NOTE: must exclude any tokens used in the yield
    // Controller role - withdraw should return to Controller
    function withdrawOther(address _asset) external virtual returns (uint256 balance) {
        _onlyController();
        _onlyNotProtectedTokens(_asset);

        balance = IERC20Upgradeable(_asset).balanceOf(address(this));
        IERC20Upgradeable(_asset).safeTransfer(controller, balance);
    }

    function balanceOfWant() public view returns (uint256) {
        return IERC20Upgradeable(want).balanceOf(address(this));
    }

    /// Tokens used in yeild process, should not be available to withdraw via withdrawOther()
    function _onlyNotProtectedTokens(address _asset) internal virtual;
}
