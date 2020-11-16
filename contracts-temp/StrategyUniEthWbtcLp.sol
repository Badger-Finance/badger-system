// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IStakingRewards.sol";

import "interfaces/badger/IController.sol";

/*
    Based on pickle.finance strategy: https://github.com/pickle-finance/contracts/blob/master/PickleJars/strategies/StrategyUniEthDaiLpV3.sol
    Modifications:
    * Updated to solidity 0.6.x
    * Uses immutable for constant addresses
    * Modified for UniEthWbtc pool
    * Does not burn Pickle
    * burnFee removed (as per previous)
    * Performance fee to YFI standard
    * TODO gate harvesting to strategist or governance
*/ 
contract StrategyUniEthWbtcLp {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    address public constant want = 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11; // Want: Uniswap eth/wbtc LP tokens
    address public constant stakingRewards = 0xa1484C3aa22a66C62b77E0AE78E15258bd0cB711; // Staking stakingRewards address for ETH/WBTC LP providers
    address public constant uniToken = 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984; // tokens we're farming
    address public constant dai = 0x6B175474E89094C44Da98b954EedeAC495271d0F; // stablecoins
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // weth
    address public constant univ2Router2 = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D; // Uniswap Dex

    uint256 public keepUNI = 0; // How many UNI tokens to keep? 0 by default.
    uint256 public constant keepUNIMax = 10000;

    uint256 public performanceFee = 450;
    uint256 public constant performanceMax = 10000;

    uint256 public withdrawalFee = 50;
    uint256 public constant withdrawalMax = 10000;

    address public governance;
    address public controller;
    address public strategist;

    constructor(
        address _governance,
        address _strategist,
        address _controller
    ) public {
        governance = _governance;
        strategist = _strategist;
        controller = _controller;
    }

    // **** Views ****
    function balanceOfWant() public view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    function balanceOfPool() public view returns (uint256) {
        return IStakingRewards(stakingRewards).balanceOf(address(this));
    }

    function balanceOf() public view returns (uint256) {
        return balanceOfWant().add(balanceOfPool());
    }

    function getName() external pure returns (string memory) {
        return "StrategyUniEthDaiLpV3";
    }

    function getHarvestable() external view returns (uint256) {
        return IStakingRewards(stakingRewards).earned(address(this));
    }

    // **** Setters ****
    function setKeepUNI(uint256 _keepUNI) external {
        require(msg.sender == governance, "!governance");
        keepUNI = _keepUNI;
    }

    function setWithdrawalFee(uint256 _withdrawalFee) external {
        require(msg.sender == governance, "!governance");
        withdrawalFee = _withdrawalFee;
    }

    function setPerformanceFee(uint256 _performanceFee) external {
        require(msg.sender == governance, "!governance");
        performanceFee = _performanceFee;
    }

    function setStrategist(address _strategist) external {
        require(msg.sender == governance, "!governance");
        strategist = _strategist;
    }

    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        governance = _governance;
    }

    function setController(address _controller) external {
        require(msg.sender == governance, "!governance");
        controller = _controller;
    }

    // **** State Mutations ****
    function deposit() public {
        uint256 _want = IERC20(want).balanceOf(address(this));
        if (_want > 0) {
            IERC20(want).safeApprove(stakingRewards, 0);
            IERC20(want).approve(stakingRewards, _want);
            IStakingRewards(stakingRewards).stake(_want);
        }
    }

    // Controller only function for creating additional rewards from dust
    function withdrawOther(IERC20 _asset) external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        require(want != _asset, "want");
        balance = IERC20Upgradeable(_asset).balanceOf(address(this));
        IERC20Upgradeable(_asset).safeTransfer(controller, balance);
    }

    // Contoller only function for withdrawing for free
    // This is used to swap between vaults
    function freeWithdraw(uint256 _amount) external {
        require(msg.sender == controller, "!controller");
        uint256 _balance = IERC20(want).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _withdrawSome(_amount.sub(_balance));
            _amount = _amount.add(_balance);
        }
        IERC20(want).safeTransfer(msg.sender, _amount);
    }

    // Withdraw partial funds, normally used with a vault withdrawal
    function withdraw(uint256 _amount) external {
        require(msg.sender == controller, "!controller");
        uint256 _balance = IERC20(want).balanceOf(address(this));
        if (_balance < _amount) {
            _amount = _withdrawSome(_amount.sub(_balance));
            _amount = _amount.add(_balance);
        }

        uint256 _fee = _amount.mul(withdrawalFee).div(withdrawalMax);

        IERC20(want).safeTransfer(IController(controller).rewards(), _fee);
        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds

        IERC20(want).safeTransfer(_vault, _amount.sub(_fee));
    }

    // Withdraw all funds, normally used when migrating strategies
    function withdrawAll() external returns (uint256 balance) {
        require(msg.sender == controller, "!controller");
        _withdrawAll();

        balance = IERC20(want).balanceOf(address(this));

        address _vault = IController(controller).vaults(address(want));
        require(_vault != address(0), "!vault"); // additional protection so we don't burn the funds
        IERC20(want).safeTransfer(_vault, balance);
    }

    function harvest() public {
        require(msg.sender == strategist || msg.sender == governance, "!authorized");

        // Collects UNI tokens
        IStakingRewards(stakingRewards).getReward();
        uint256 _uniTokenBalance = IERC20(uniToken).balanceOf(address(this));
        if (_uniTokenBalance > 0) {
            // 10% is locked up for future gov
            uint256 _keepUNI = _uniTokenBalance.mul(keepUNI).div(keepUNIMax);
            IERC20(uniToken).safeTransfer(
                IController(controller).rewards(),
                _keepUNI
            );
            _swap(uniToken, weth, _uniTokenBalance.sub(_keepUNI));
        }

        // Swap half WETH for DAI
        uint256 _weth = IERC20(weth).balanceOf(address(this));
        if (_weth > 0) {
            _swap(weth, dai, _weth.div(2));
        }

        // Adds in liquidity for ETH/DAI
        _weth = IERC20(weth).balanceOf(address(this));
        uint256 _dai = IERC20(dai).balanceOf(address(this));
        if (_weth > 0 && _dai > 0) {
            IERC20(weth).safeApprove(univ2Router2, 0);
            IERC20(weth).safeApprove(univ2Router2, _weth);

            IERC20(dai).safeApprove(univ2Router2, 0);
            IERC20(dai).safeApprove(univ2Router2, _dai);

            IUniswapRouterV2(univ2Router2).addLiquidity(
                weth,
                dai,
                _weth,
                _dai,
                0,
                0,
                address(this),
                now + 60
            );

            // Donates DUST
            IERC20(weth).transfer(
                IController(controller).rewards(),
                IERC20(weth).balanceOf(address(this))
            );
            IERC20(dai).transfer(
                IController(controller).rewards(),
                IERC20(dai).balanceOf(address(this))
            );
        }

        // We want to get back UNI ETH/DAI LP tokens
        uint256 _want = IERC20(want).balanceOf(address(this));
        if (_want > 0) {
            // Performance fee
            IERC20(want).safeTransfer(
                IController(controller).rewards(),
                _want.mul(performanceFee).div(performanceMax)
            );

            deposit();
        }
    }

    /// @notice Emergency function call
    /// @dev This effectively allows for the governance to execute _any_ function in the Strategy context.
    function execute(address _target, bytes memory _data)
        public
        payable
        returns (bytes memory response)
    {
        require(msg.sender == governance, "!governance");
        require(_target != address(0), "!target");

        // call contract in current context
        assembly {
            let succeeded := delegatecall(
                sub(gas(), 5000),
                _target,
                add(_data, 0x20),
                mload(_data),
                0,
                0
            )
            let size := returndatasize()

            response := mload(0x40)
            mstore(
                0x40,
                add(response, and(add(add(size, 0x20), 0x1f), not(0x1f)))
            )
            mstore(response, size)
            returndatacopy(add(response, 0x20), 0, size)

            switch iszero(succeeded)
                case 1 {
                    // throw if delegatecall failed
                    revert(add(response, 0x20), size)
                }
        }
    }

    // **** Internal functions ****
    function _swap(
        address _from,
        address _to,
        uint256 _amount
    ) internal {
        // Swap with uniswap
        IERC20(_from).safeApprove(univ2Router2, 0);
        IERC20(_from).safeApprove(univ2Router2, _amount);

        address[] memory path;

        if (_from == weth || _to == weth) {
            path = new address[](2);
            path[0] = _from;
            path[1] = _to;
        } else {
            path = new address[](3);
            path[0] = _from;
            path[1] = weth;
            path[2] = _to;
        }

        IUniswapRouterV2(univ2Router2).swapExactTokensForTokens(
            _amount,
            0,
            path,
            address(this),
            now.add(60)
        );
    }

    function _withdrawAll() internal {
        _withdrawSome(balanceOfPool());
    }

    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        IStakingRewards(stakingRewards).withdraw(_amount);
        return _amount;
    }
}
