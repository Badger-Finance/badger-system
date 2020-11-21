// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapPair.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/pickle/IPickleJar.sol";
import "interfaces/pickle/IPickleChef.sol";
import "interfaces/pickle/IPickleStaking.sol";
import "interfaces/erc20/IWETH.sol";

import "../BaseStrategy.sol";

/* StrategyPickleMetaFarm
    A "meta-vault" strategy that deposits the want into the appropriate PickleJar. The recieved 'pWant' tokens are staked into the appropriate farm to increase rewards. Pickle gathered from this can be periodically 'recycled' into the Pickle farm to compound rewards.

    Parts of this implementation are inspired by bantegs' StrategyUniswapPairPickle for Yearn Vaults V2:
    https://github.com/banteg/strategy-uni-lp-pickle/blob/master/contracts/StrategyUniswapPairPickle.sol
*/
contract StrategyPickleMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public pickleJar;
    uint256 public pid; // Pickle Chef Token ID
    address public curveSwap; // Curve renBtc Swap
    address public lpComponent; // wBTC for renCrv and sCrv

    address public constant pickle = 0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5;
    address public constant pickleChef = 0xbD17B1ce622d73bD438b9E658acA5996dc394b0d;
    address public constant pickleStaking = 0xa17a8883dA1aBd57c690DF9Ebf58fC194eDAb66F;

    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599;

    uint256 public picklePerformanceFeeGovernance;
    uint256 public picklePerformanceFeeStrategist;

    uint256 public lastHarvested;

    event NotifyWithdrawMismatch(uint256 expected, uint256 actual, uint256 remainingStaked);
    event Tend(uint256 tended, uint256 wethHarvested);
    event WethConverted(uint256 amount);

    event PickleHarvest(
        uint256 preExistingPickle,
        uint256 fromStakingRewards,
        uint256 totalHarvested,
        uint256 ethConverted,
        uint256 wethHarvested,
        uint256 wbtcDeposited,
        uint256 want,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee,
        uint256 timestamp,
        uint256 blockNumber
    );

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[4] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        pickleJar = _wantConfig[1];
        curveSwap = _wantConfig[2];
        lpComponent = _wantConfig[3];

        pid = _pid;

        (address lp, , , ) = IPickleChef(pickleChef).poolInfo(pid);

        // // Confirm pickle-related addresses
        require(IPickleJar(pickleJar).token() == address(want), "PickleJar & Want mismatch");
        require(lp == pickleJar, "pid & Pickle jar mismatch");

        picklePerformanceFeeGovernance = _feeConfig[0];
        picklePerformanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Grant infinite approval to Pickle
        IERC20Upgradeable(want).safeApprove(pickleJar, type(uint256).max);
        IERC20Upgradeable(pickleJar).safeApprove(pickleChef, type(uint256).max);
        IERC20Upgradeable(pickle).safeApprove(pickleStaking, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyPickleMetaFarm";
    }

    // TODO: Return a valid balance of pool
    function balanceOfPool() public override view returns (uint256) {
        (uint256 _staked, ) = IPickleChef(pickleChef).userInfo(pid, address(this));
        return _staked;
    }

    function isTendable() public override view returns (bool) {
        return true;
    }

    /// ===== Permissioned Actions: Governance =====

    function setPicklePerformanceFeeStrategist(uint256 _picklePerformanceFeeStrategist) external {
        _onlyGovernance();
        picklePerformanceFeeStrategist = _picklePerformanceFeeStrategist;
    }

    function setPicklePerformanceFeeGovernance(uint256 _picklePerformanceFeeGovernance) external {
        _onlyGovernance();
        picklePerformanceFeeGovernance = _picklePerformanceFeeGovernance;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(want != _asset, "want");
        require(pickleJar != _asset, "pickleJar");
        require(pickle != _asset, "pickle");
    }

    /// @notice Deposit any want in the strategy into the mechanics
    /// @dev want -> pickleJar, pWant -> pWantFarm (handled in postDeposit hook)
    function _deposit(uint256 _want) internal override {
        if (_want > 0) {
            IPickleJar(pickleJar).deposit(_want);
        }
    }

    function _postDeposit() internal override {
        uint256 _jar = IERC20Upgradeable(pickleJar).balanceOf(address(this));
        if (_jar > 0) {
            IPickleChef(pickleChef).deposit(pid, _jar);
        }
    }

    /// @dev Transfer non-harvested rewards directly to rewards contract
    function _withdrawAll() internal override {
        IPickleStaking(pickleStaking).getReward();
        IPickleStaking(pickleStaking).exit();

        (uint256 _staked, ) = IPickleChef(pickleChef).userInfo(pid, address(this));
        IPickleChef(pickleChef).withdraw(pid, _staked);

        uint256 _weth = IERC20Upgradeable(weth).balanceOf(address(this));
        uint256 _pickle = IERC20Upgradeable(pickle).balanceOf(address(this));

        IERC20Upgradeable(weth).transfer(IController(controller).rewards(), _weth);
        IERC20Upgradeable(pickle).transfer(IController(controller).rewards(), _pickle);
    }

    /// @notice Partially withdraw from strategy, unrolling rewards
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));

        // Determine number of pToken shares in Chef
        (uint256 _staked, ) = IPickleChef(pickleChef).userInfo(pid, address(this));

        // Determine the amount of pTokens to withdraw to recieve the correct amount of want, based on the ratio between pTokens and want
        uint256 _withdraw = _amount.mul(1e18).div(IPickleJar(pickleJar).getRatio());

        // Banteg's Note: This could result in less amount freed because of rounding error
        IPickleChef(pickleChef).withdraw(pid, MathUpgradeable.min(_staked, _withdraw));

        // Banteg's Note: This could result in less amount freed because of withdrawal fees
        uint256 _jar = IERC20Upgradeable(pickleJar).balanceOf(address(this));
        IPickleJar(pickleJar).withdraw(_jar);

        // TODO: Test code, consider removing to save a little on gas
        uint256 _after = IERC20Upgradeable(want).balanceOf(address(this));
        if (_amount != _after.sub(_before)) {
            (uint256 _stakedAfter, ) = IPickleChef(pickleChef).userInfo(pid, address(this));
            emit NotifyWithdrawMismatch(_amount, _after.sub(_before), _stakedAfter);
        }

        // Return the actual amount withdrawn if less than requested
        return MathUpgradeable.min(_after.sub(_before), _amount);
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external override whenNotPaused {
        _onlyAuthorizedActors();

        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));
        uint256 _beforeEth = address(this).balance;

        // Harvest WETH Rewards & Unstake Pickle
        IPickleStaking(pickleStaking).exit();

        uint256 _afterPickleStakingExit = IERC20Upgradeable(pickle).balanceOf(address(this));

        // Harvest WETH gains
        IPickleStaking(pickleStaking).getReward();

        // Harvest Pickle gains
        _harvestPickle();
        uint256 _pickle = IERC20Upgradeable(pickle).balanceOf(address(this));

        lastHarvested = now;

        uint256 _governanceFee = 0;
        uint256 _strategistFee = 0;

        // Convert any Pickle to ETH, after fees
        if (_pickle > 0) {
            _governanceFee = _processFee(pickle, _pickle, picklePerformanceFeeGovernance, governance);
            _strategistFee = _processFee(pickle, _pickle, picklePerformanceFeeStrategist, strategist);

            uint256 _remaining = IERC20Upgradeable(pickle).balanceOf(address(this));

            address[] memory path = new address[](2);
            path[0] = pickle;
            path[1] = weth;

            _swapEthOut(pickle, _remaining, path);
        }

        uint256 _weth = IERC20Upgradeable(pickle).balanceOf(address(this));
        if (_weth > 0) {
            IWETH(weth).withdraw(_weth);
        }

        uint256 _eth = address(this).balance;

        // Unwrap WETH to ETH, convert to WBTC in order to add to LP position
        if (_eth > 0) {
            _eth = address(this).balance;

            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = wbtc;

            _swapEthIn(_eth, path);
        }

        // Add wBTC to increase LP position
        uint256 _lpComponent = IERC20Upgradeable(wbtc).balanceOf(address(this));
        if (_lpComponent > 0) {
            _safeApproveHelper(wbtc, curveSwap, _lpComponent);
            ICurveFi(curveSwap).add_liquidity([0, _lpComponent], 0);
        }

        // Deposit new want into position
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));
        if (_want > 0) {
            _deposit(_want);
        }

        emit PickleHarvest(
            _before,
            _afterPickleStakingExit.sub(_before),
            _pickle,
            _eth.sub(_beforeEth),
            _weth,
            _lpComponent,
            _want,
            _governanceFee,
            _strategistFee,
            now,
            block.number
        );
        emit Harvest(_want.sub(_before), block.number);
    }

    /// @notice Compound PICKLE and WETH gained from farms into more pickle for staking rewards
    /// @notice Any excess PICKLE sitting in the Strategy will be staked as well
    function tend() external whenNotPaused returns (uint256) {
        _onlyAuthorizedActors();

        // Harvest WETH gains
        IPickleStaking(pickleStaking).getReward();
        uint256 _weth = IERC20Upgradeable(pickle).balanceOf(address(this));

        // Convert WETH into Pickle
        if (_weth > 0) {
            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = pickle;

            _swap(weth, _weth, path);
        }

        // Harvest Pickle from Chef
        _harvestPickle();
        uint256 _pickle = IERC20Upgradeable(pickle).balanceOf(address(this));

        // Deposit gathered PICKLE into staking to increase WETH
        if (_pickle > 0) {
            _safeApproveHelper(pickle, pickleStaking, _pickle);
            IPickleStaking(pickleStaking).stake(_pickle);
        }

        emit Tend(_pickle, _weth);
        return _pickle;
    }

    /// ===== Internal Helper Functions =====

    /// @notice Realize Pickle gains by depositing zero (Pickle is harvested on any deposit or withdraw)
    function _harvestPickle() internal {
        IPickleChef(pickleChef).deposit(pid, 0);
    }

    /// @dev PickleMetaFarm needs to be able to recieve ETH to execute Uni trades.
    /// @dev Only Uniswap Router is able to send ETH
    receive() external payable {}

    // require(msg.sender == uniswap, "Only accept ETH from Uniswap");
}
