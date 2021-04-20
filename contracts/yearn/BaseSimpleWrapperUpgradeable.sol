// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

import "interfaces/yearn/VaultApi.sol";
import "interfaces/yearn/RegistryApi.sol";

abstract contract BaseSimpleWrapperUpgradeable is Initializable {
    using MathUpgradeable for uint256;
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    IERC20Upgradeable public token;

    // Reduce number of external calls (SLOADs stay the same)
    VaultAPI[] private _cachedVaults;

    RegistryAPI public registry;

    // ERC20 Unlimited Approvals (short-circuits VaultAPI.transferFrom)
    uint256 constant UNLIMITED_APPROVAL = type(uint256).max;
    // Sentinal values used to save gas on deposit/withdraw/migrate
    // NOTE: DEPOSIT_EVERYTHING == WITHDRAW_EVERYTHING == MIGRATE_EVERYTHING
    uint256 constant DEPOSIT_EVERYTHING = type(uint256).max;
    uint256 constant WITHDRAW_EVERYTHING = type(uint256).max;
    uint256 constant MIGRATE_EVERYTHING = type(uint256).max;
    // VaultsAPI.depositLimit is unlimited
    uint256 constant UNCAPPED_DEPOSITS = type(uint256).max;

    function _BaseSimpleWrapperUpgradeable_init(address _token, address _registry) internal initializer {
        token = IERC20Upgradeable(_token);
        // v2.registry.ychad.eth
        registry = RegistryAPI(_registry);
    }

    function setRegistry(address _registry) external {
        require(msg.sender == registry.governance());
        // In case you want to override the registry instead of re-deploying
        registry = RegistryAPI(_registry);
        // Make sure there's no change in governance
        // NOTE: Also avoid bricking the wrapper from setting a bad registry
        require(msg.sender == registry.governance());
    }
}
