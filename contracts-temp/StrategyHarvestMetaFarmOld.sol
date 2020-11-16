// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/harvest/IDepositHelper.sol";
import "interfaces/harvest/IHarvestVault.sol";
import "interfaces/harvest/IRewardPool.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";

contract StrategyHarvest {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    address public immutable want;

    address public immutable harvestVault; // Harvest vault for want
    address public immutable wantStakingPool; // Farm staking contract for want

    address public constant farm = 0xa0246c9032bC3A600820415aE600c6388619A14D; // FARM token
    address public constant depositHelper = 0xF8ce90c2710713552fb564869694B2505Bfc0846; // Farm vault deposit helper
    address public constant farmProfitSharingPool = 0xae024F29C26D6f71Ec71658B1980189956B0546D; // Farm staking contract for want

    string internal _vaultName;

    // All fees in basis points
    uint256 public performanceFee = 450;
    uint256 public constant performanceMax = 10000;

    uint256 public withdrawalFee = 50;
    uint256 public constant withdrawalMax = 10000;

    uint256 public constant keepFARM = 10000;

    uint256 public constant farmFee = 100;
    uint256 public constant farmFeeMax = 10000;

    address public governance;
    address public controller;
    address public strategist;

    constructor(
        address _governance,
        address _strategist,
        address _controller,
        address _want,
        address _harvestVault,
        address _farmRewards,
        string memory vaultName
    ) public {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;
        want = _want;
        harvestVault = _harvestVault;
        wantStakingPool = _farmRewards;

        _vaultName = vaultName;
    }

    function getName() external view returns (string memory) {
        return _vaultName;
    }

    function setStrategist(address _strategist) external {
        require(msg.sender == governance, "!governance");
        strategist = _strategist;
    }

    function setWithdrawalFee(uint256 _withdrawalFee) external {
        require(msg.sender == governance, "!governance");
        withdrawalFee = _withdrawalFee;
    }

    function setPerformanceFee(uint256 _performanceFee) external {
        require(msg.sender == governance, "!governance");
        performanceFee = _performanceFee;
    }

    /// @dev Deposit all want into the corresponding Harvest vault
    function deposit() public {
        uint256 _depositAmount = IERC20(want).balanceOf(address(this));
        if (_depositAmount > 0) {
            IERC20(want).safeApprove(depositHelper, 0);
            IERC20(want).safeApprove(depositHelper, _depositAmount);

            uint256[] memory amounts = new uint256[](1);
            address[] memory tokens = new address[](1);

            amounts[0] = _depositAmount;
            tokens[0] = want;

            IDepositHelper(depositHelper).depositAll(amounts, tokens);
        }
    }

    // Controller only function for creating additional rewards from dust
    function withdrawOther(IERC20 _asset) external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        require(want != _asset, "want");
        require(farm != _asset, "farm");
        balance = IERC20Upgradeable(_asset).balanceOf(address(this));
        IERC20Upgradeable(_asset).safeTransfer(controller, balance);
    }

    // Withdraw partial funds, normally used with a vault withdrawal
    function withdraw(uint256 _amount) external {
        require(msg.sender == controller, "!controller");
        uint256 _balance = IERC20(want).balanceOf(address(this));

        // If we don't have enough excess want in the strategy to cover the withdraw, we need to withdraw from wherever the want is gathering yeild.
        if (_balance < _amount) {
            _amount = _withdrawSome(_amount.sub(_balance));
            _amount = _amount.add(_balance);
        }

        uint256 _fee = _amount.mul(withdrawalFee).div(withdrawalMax); // Take a fee on withdraw
        IERC20(want).safeTransfer(IController(controller).rewards(), _fee);

        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!harvestVault"); // additional protection so we don't burn the funds

        IERC20(want).safeTransfer(_vault, _amount.sub(_fee));
    }

    // Withdraw all funds, normally used when migrating strategies
    function withdrawAll() external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        _withdrawAll();

        balance = IERC20(want).balanceOf(address(this));

        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!harvestVault"); // additional protection so we don't burn the funds
        IERC20(want).safeTransfer(_vault, balance);
    }

    function _withdrawAll() internal {
        // Withdraw entire balance from Harvest vault
        uint256 balance = IHarvestVault(harvestVault).balanceOf(address(this));
        _withdrawSome(balance);
    }

    function emergencyWithdraw(bytes memory data) public {
        require(msg.sender == controller, "!controller");
    }

    /// @notice Move accumulated FARM rewards to the FARM profit sharing pool to increase rewards
    function harvest() public {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");
        IRewardPool(wantStakingPool).getReward(); // Harvest FARM from deposits

        uint256 _farmBalance = IERC20(farm).balanceOf(stake);

        if (_farmBalance > 0) {
            IRewardPool(farmProfitSharingPool).stake(_farmBalance);
        }
    }

    /// @notice Withdraw some from Harvest vault, forwarding the appropraite proportion of accumulated FARM Rewards
    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        // Harvest reward pool
        // if (staked in profit sharing > amount ) {
            // Take YOUR proportion of FARM rewards out of the profit sharing

            // The amount we want to UNSTAKE is the USERS proprotionm of the farm rewards IN THERE
            IRewardPool(farmProfitSharingPool).unstake(_amount);

            uint256 profitSharingRewards = IERC20(farm).balanceOf(address(this)).sub();
            // Take YOUR proportion of FARM rewards, from the profit sharing amount
        // }
            IRewardPool(wantStakingPool).withdraw(_amount); //TODO: Is the number of shares different than the amount of underlying?
            IHarvestVault(harvestVault).withdraw(_amount); //TODO: Is the amount of fTokens different than the amount of underlying?

        // TODO: What about emergency withdraw?

        return _amount;
    }

    function balanceOfWant() public view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    function balanceOfPool() public view returns (uint256) {
        return IHarvestVault(harvestVault).balanceOf(address(this));
    }

    function balanceOf() public view returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }

    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        governance = _governance;
    }

    function setController(address _controller) external {
        require(msg.sender == governance, "!governance");
        controller = _controller;
    }
}
