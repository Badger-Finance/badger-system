//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts/math/SafeMath.sol";

import "./SmartVesting.sol";

/*
    Simple OTC Escrow contract to transfer vested bBadger in exchange for specified USDC amount
*/
contract OtcEscrow {
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    address constant usdc = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant bBadger = 0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28;
    address constant badgerGovernance = 0xB65cef03b9B89f99517643226d76e286ee999e77;

    event VestingDeployed(address vesting);

    address beneficiary;
    uint256 cliffDuration;
    uint256 duration;
    uint256 usdcAmount;
    uint256 bBadgerAmount;

    constructor(
        address beneficiary_,
        uint256 cliffDuration_,
        uint256 duration_,
        uint256 usdcAmount_,
        uint256 bBadgerAmount_
    ) public {
        beneficiary = beneficiary_;
        cliffDuration = cliffDuration_;
        duration = duration_;
        usdcAmount = usdcAmount_;
        bBadgerAmount = bBadgerAmount_;
    }

    modifier onlyApprovedParties() {
        require(msg.sender == badgerGovernance || msg.sender == beneficiary);
        _;
    }

    /// @dev Atomically trade specified amonut of USDC for control over bBadger in SmartVesting contract
    /// @dev Either counterparty may execute swap if sufficient token approval is given by recipient
    function swap() public onlyApprovedParties {
        // Transfer expected USDC from beneficiary
        IERC20(usdc).safeTransferFrom(beneficiary, address(this), usdcAmount);

        // Create Vesting contract
        SmartVesting vesting = new SmartVesting();

        vesting.initialize(
            IERC20Upgradeable(bBadger),
            beneficiary,
            badgerGovernance,
            now,
            cliffDuration,
            duration
        );

        // Transfer bBadger to vesting contract
        uint256 bBadgerBalance = IERC20(bBadger).balanceOf(address(this));
        require(bBadgerBalance == bBadgerAmount);
        IERC20(bBadger).safeTransfer(address(vesting), bBadgerBalance);

        // Transfer USDC to badger governance 
        IERC20(usdc).safeTransfer(badgerGovernance, usdcAmount);

        emit VestingDeployed(address(vesting));
    }

    /// @dev Return bBadger to Badger Governance to revoke escrow deal
    function revoke() external onlyApprovedParties {
        uint256 bBadgerBalance = IERC20(bBadger).balanceOf(address(this));
        IERC20(bBadger).safeTransfer(badgerGovernance, bBadgerBalance);
    }
}
