//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/TokenTimelockUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

contract SimpleTimelock is TokenTimelockUpgradeable {
    using SafeMathUpgradeable for uint256;

    function initialize(
        IERC20Upgradeable token,
        address beneficiary,
        uint256 releaseTime
    ) public initializer {
        __TokenTimelock_init(token, beneficiary, releaseTime);
    }
}
