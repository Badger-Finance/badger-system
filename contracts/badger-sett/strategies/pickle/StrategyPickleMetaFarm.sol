// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

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
    event Tend(uint256 pickleTended, uint256 wethConverted);

    event PickleHarvest(
        uint256 pickleFromStakingRewards,
        uint256 pickleFromHarvest,
        uint256 totalPickleToConvert,
        uint256 pickleRecycled,
        uint256 ethConverted,
        uint256 wethHarvested,
        uint256 lpComponentDeposited,
        uint256 lpDeposited,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 preExistingWant;
        uint256 preExistingPickle;
        uint256 pickleFromStakingRewards;
        uint256 pickleFromHarvest;
        uint256 totalPickleToConvert;
        uint256 pickleRecycled;
        uint256 ethConverted;
        uint256 wethHarvested;
        uint256 lpComponentDeposited;
        uint256 lpDeposited;
        uint256 lpPositionIncrease;
        uint256 governancePerformanceFee;
        uint256 strategistPerformanceFee;
    }

    struct TendData {
        uint256 pickleTended;
        uint256 wethConverted;
    }

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

    function getProtectedTokens() external view override returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = pickleJar;
        protectedTokens[2] = pickle;
        return protectedTokens;
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
        uint256 _stakedPickle = IPickleStaking(pickleStaking).balanceOf(address(this));

        if (_stakedPickle > 0) {
            IPickleStaking(pickleStaking).exit();
        }

        // Unstake all pWant from Chef
        (uint256 _pSharesStaked, ) = IPickleChef(pickleChef).userInfo(pid, address(this));

        if (_pSharesStaked > 0) {
            IPickleChef(pickleChef).withdraw(pid, _pSharesStaked);
        }

        // Withdraw from pickle vault
        IPickleJar(pickleJar).withdrawAll();

        // Send un-harvested rewards to rewards contract
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
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        harvestData.preExistingWant = IERC20Upgradeable(want).balanceOf(address(this));
        harvestData.preExistingPickle = IERC20Upgradeable(pickle).balanceOf(address(this));

        uint256 _stakedPickle = IPickleStaking(pickleStaking).balanceOf(address(this));

        // Harvest WETH Rewards & Unstake Pickle
        if (_stakedPickle > 0) {
            IPickleStaking(pickleStaking).exit();
        }

        uint256 _afterPickleStakingExit = IERC20Upgradeable(pickle).balanceOf(address(this));
        harvestData.pickleFromStakingRewards = _afterPickleStakingExit.sub(harvestData.preExistingPickle);

        // Harvest WETH gains
        IPickleStaking(pickleStaking).getReward();

        // Harvest Pickle gains
        _harvestPickle();

        harvestData.totalPickleToConvert = IERC20Upgradeable(pickle).balanceOf(address(this));

        harvestData.pickleFromHarvest = harvestData.totalPickleToConvert.sub(
            harvestData.pickleFromStakingRewards.sub(harvestData.preExistingPickle)
        );

        lastHarvested = now;

        // Convert any Pickle to ETH, after fees
        if (harvestData.totalPickleToConvert > 0) {
            harvestData.governancePerformanceFee = _processFee(
                pickle,
                harvestData.totalPickleToConvert,
                picklePerformanceFeeGovernance,
                governance
            );
            harvestData.strategistPerformanceFee = _processFee(
                pickle,
                harvestData.totalPickleToConvert,
                picklePerformanceFeeStrategist,
                strategist
            );

            harvestData.pickleRecycled = IERC20Upgradeable(pickle).balanceOf(address(this));

            address[] memory path = new address[](2);
            path[0] = pickle;
            path[1] = weth;

            _swapEthOut(pickle, harvestData.pickleRecycled, path);
        }

        harvestData.wethHarvested = IERC20Upgradeable(pickle).balanceOf(address(this));
        if (harvestData.wethHarvested > 0) {
            IWETH(weth).withdraw(harvestData.wethHarvested);
        }

        harvestData.ethConverted = address(this).balance;

        // Unwrap WETH to ETH, convert to WBTC in order to add to LP position
        if (harvestData.ethConverted > 0) {
            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = wbtc;

            _swapEthIn(harvestData.ethConverted, path);
        }

        // Add wBTC to increase LP position
        harvestData.lpComponentDeposited = IERC20Upgradeable(wbtc).balanceOf(address(this));
        if (harvestData.lpComponentDeposited > 0) {
            _safeApproveHelper(wbtc, curveSwap, harvestData.lpComponentDeposited);
            ICurveFi(curveSwap).add_liquidity([0, harvestData.lpComponentDeposited], 0);
        }

        // Deposit new want into position
        harvestData.lpDeposited = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.lpDeposited > 0) {
            _deposit(harvestData.lpDeposited);
            _postDeposit();
        }

        harvestData.lpPositionIncrease = harvestData.lpDeposited.sub(harvestData.preExistingWant);

        emit PickleHarvest(
            harvestData.pickleFromStakingRewards,
            harvestData.pickleFromHarvest,
            harvestData.totalPickleToConvert,
            harvestData.pickleRecycled,
            harvestData.ethConverted,
            harvestData.wethHarvested,
            harvestData.lpComponentDeposited,
            harvestData.lpDeposited,
            harvestData.governancePerformanceFee,
            harvestData.strategistPerformanceFee,
            now,
            block.number
        );
        emit Harvest(harvestData.lpPositionIncrease, block.number);

        return harvestData;
    }

    /// @notice Compound PICKLE and WETH gained from farms into more pickle for staking rewards
    /// @notice Any excess PICKLE sitting in the Strategy will be staked as well
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // Harvest WETH gains
        IPickleStaking(pickleStaking).getReward();
        tendData.wethConverted = IERC20Upgradeable(pickle).balanceOf(address(this));

        // Convert WETH into Pickle
        if (tendData.wethConverted > 0) {
            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = pickle;

            _swap(weth, tendData.wethConverted, path);
        }

        // Harvest Pickle from Chef
        _harvestPickle();
        tendData.pickleTended = IERC20Upgradeable(pickle).balanceOf(address(this));

        // Deposit gathered PICKLE into staking to increase WETH
        if (tendData.pickleTended > 0) {
            _safeApproveHelper(pickle, pickleStaking, tendData.pickleTended);
            IPickleStaking(pickleStaking).stake(tendData.pickleTended);
        }

        emit Tend(tendData.pickleTended, tendData.wethConverted);
        return tendData;
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
