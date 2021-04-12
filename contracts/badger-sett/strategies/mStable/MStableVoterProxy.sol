// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

import "interfaces/mStable/IMStableAsset.sol";
import "interfaces/mStable/IMStableBoostedVault.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "../../SettAccessControl.sol";

import "./IMStableVoterProxy.sol";

// Dumb contract that:
//  - manages stake in mStable staking https://governance.mstable.org/#/stake
//  - deposits & withdraws from mStable vaults
//  - claims rewards from mStable vaults and returns to sender
//  - returns balance of caller in vault
// Extra:
//  - migrate from staking v1 to v2
//  - pay back loan if any
//  - direct boost if required
contract MStableVoterProxy is IMStableVoterProxy, PausableUpgradeable, SettAccessControl {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    mapping(address => address) public strategies; // strategy => vault
    address public votingLockup;
    uint256 public endTime; // Maximum lock length

    // TODO - add loan data here?

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[3] memory _config,
        uint256[2] memory _vaultConfig
    ) public initializer {
        __Pausable_init();
        governance = _governance;
        strategist = _strategist;
        keeper = _keeper;
        controller = _controller;
        guardian = _guardian;

        // TODO - cleanout unused config from inti fn
        votingLockup = _config[0];

        IERC20Upgradeable(want).safeApprove(gauge, type(uint256).max);
    }

    // VOTING LOCKUP

    // Init lock in VotingLock
    function createLock() external override {}

    // Claims MTA rewards from Staking and reinvests
    function reinvestMta() external override {}

    // Exits the lock and keeps MTA in contract
    function exitLock() external override returns (uint256 mtaBalance) {}

    // Upgrades the lock address
    function changeLockAddress(address _newLock, uint256 _endTime) external override {}

    // Repays the initially loaned MTA amount
    function repayLoan() external override {}

    // STRATEGIES

    // Adds a new supported strategy, looking up want and approving to vault
    function supportStrategy(address _strategy, address _vault) external override {}

    // POOL

    // Transfers _amt from sender and deposits to pool
    function deposit(address _token, uint256 _amt) external override {}

    // Withdraws balance from vault, returning to strategy
    function withdrawAll() external override {}

    // Withdraws _amt from vault, returning to strategy
    function withdrawSome(uint256 _amt) external override {}

    // fetch immediate unlock and then claim all & xfer
    // return subtracted amt
    function claim() external override returns (uint256 vestedMta) {}
}
