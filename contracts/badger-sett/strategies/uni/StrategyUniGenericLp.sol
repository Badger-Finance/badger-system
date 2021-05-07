// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapV2Factory.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";

import "../BaseStrategy.sol";

/*
    Generic uniswap lp strategy.
*/
contract StrategyUniGenericLp is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[1] memory _wantConfig,
        uint256[1] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];

        // NB: This strategy has no performance fee since there are no native uni rewards.
        withdrawalFee = _feeConfig[0];
    }

    /// ===== View Functions =====
    function getName() external override pure returns (string memory) {
        return "StrategyUniGenericLp";
    }

    /// @dev No staking pool.
    function balanceOfPool() public override view returns (uint256) {
        return 0;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](1);
        protectedTokens[0] = want;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
    }

    /// @dev No-op deposit. No native uni rewards.
    function _deposit(uint256 _want) internal override {}

    /// @dev No-op withdraw. No staking mechanism, want is just held w/in the strategy.
    function _withdrawAll() internal override {}

    /// @dev No-op withdraw. No staking mechanism, want is just held w/in the strategy.
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        return _amount;
    }

    /// @dev No-op harvest. Rewards are handled by an off chain keeper.
    function harvest() external whenNotPaused {
        _onlyAuthorizedActors();
    }
}
