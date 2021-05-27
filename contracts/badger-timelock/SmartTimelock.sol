//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.8;

import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/TokenTimelockUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

import "./ExecutorOnlyCall.sol";

/* 
  A token timelock that is capable of interacting with other smart contracts.
  This allows the beneficiary to participate in on-chain goverance processes, despite having locked tokens.

  Features safety functions to allow beneficiary to claim ETH & ERC20-compliant tokens sent to the timelock contract, accidentially or otherwise.

  An optional 'governor' address has the ability to allow the timelock to send it's tokens to approved destinations. 
  This is intended to allow the token holder to stake their tokens in approved mechanisms.
*/

contract SmartTimelock is TokenTimelockUpgradeable, ExecutorOnlyCall, ReentrancyGuardUpgradeable {
    address internal _governor;
    mapping(address => bool) internal _transferAllowed;

    function initialize(
        IERC20Upgradeable token,
        address beneficiary,
        address governor,
        uint256 releaseTime
    ) public initializer {
        __TokenTimelock_init(token, beneficiary, releaseTime);
        __ReentrancyGuard_init_unchained();
        _governor = governor;
    }

    event Call(address to, uint256 value, bytes data, bool transfersAllowed);
    event ApproveTransfer(address to);
    event RevokeTransfer(address to);
    event ClaimToken(IERC20Upgradeable token, uint256 amount);
    event ClaimEther(uint256 amount);

    modifier onlyBeneficiary() {
        require(msg.sender == beneficiary(), "smart-timelock/only-beneficiary");
        _;
    }

    modifier onlyGovernor() {
        require(msg.sender == _governor, "smart-timelock/only-governor");
        _;
    }

    /**
     * @notice Allows the timelock to call arbitrary contracts, as long as it does not reduce it's locked token balance
     * @dev Initialization check is implicitly provided by `voteExists()` as new votes can only be
     *      created via `newVote(),` which requires initialization
     * @param to Contract address to call
     * @param value ETH value to send, if any
     * @param data Encoded data to send
     */
    function call(
        address to,
        uint256 value,
        bytes calldata data
    ) external payable onlyBeneficiary() nonReentrant() returns (bool success) {
        uint256 preAmount = token().balanceOf(address(this));

        success = execute(to, value, data, gasleft());

        if (!_transferAllowed[to]) {
            uint256 postAmount = token().balanceOf(address(this));
            require(postAmount >= preAmount, "smart-timelock/locked-balance-check");
        }

        emit Call(to, value, data, _transferAllowed[to]);
    }

    function approveTransfer(address to) external onlyGovernor() {
        _transferAllowed[to] = true;
        emit ApproveTransfer(to);
    }

    function revokeTransfer(address to) external onlyGovernor() {
        _transferAllowed[to] = false;
        emit RevokeTransfer(to);
    }

    /**
     * @notice Claim ERC20-compliant tokens other than locked token.
     * @param tokenToClaim Token to claim balance of.
     */
    function claimToken(IERC20Upgradeable tokenToClaim) external onlyBeneficiary() nonReentrant() {
        require(address(tokenToClaim) != address(token()), "smart-timelock/no-locked-token-claim");
        uint256 preAmount = token().balanceOf(address(this));

        uint256 claimableTokenAmount = tokenToClaim.balanceOf(address(this));
        require(claimableTokenAmount > 0, "smart-timelock/no-token-balance-to-claim");

        tokenToClaim.transfer(beneficiary(), claimableTokenAmount);

        uint256 postAmount = token().balanceOf(address(this));
        require(postAmount >= preAmount, "smart-timelock/locked-balance-check");

        emit ClaimToken(tokenToClaim, claimableTokenAmount);
    }

    /**
     * @notice Claim Ether in contract.
     */
    function claimEther() external onlyBeneficiary() nonReentrant() {
        uint256 preAmount = token().balanceOf(address(this));

        uint256 etherToTransfer = address(this).balance;
        require(etherToTransfer > 0, "smart-timelock/no-ether-balance-to-claim");

        payable(beneficiary()).transfer(etherToTransfer);

        uint256 postAmount = token().balanceOf(address(this));
        require(postAmount >= preAmount, "smart-timelock/locked-balance-check");

        emit ClaimEther(etherToTransfer);
    }

    /**
     * @notice Governor address
     */
    function governor() external view returns (address) {
        return _governor;
    }

    /**
     * @notice Allow timelock to receive Ether
     */
    receive() external payable {}
}
