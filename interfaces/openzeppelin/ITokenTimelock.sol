// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

/**
 * @dev A token holder contract that will allow a beneficiary to extract the
 * tokens after a given release time.
 *
 * Useful for simple vesting schedules like "advisors get all of their tokens
 * after 1 year".
 */
interface ITokenTimelock {
    /**
     * @return the token being held.
     */
    function token() external view returns (address);

    /**
     * @return the beneficiary of the tokens.
     */
    function beneficiary() external view returns (address);

    /**
     * @return the time when the tokens are released.
     */
    function releaseTime() external view returns (uint256);

    /**
     * @notice Transfers tokens held by timelock to beneficiary.
     */
    function release() external;
}
