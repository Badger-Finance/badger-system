//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/TokenTimelockUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

contract SimpleTimelock is TokenTimelockUpgradeable {
    using SafeMathUpgradeable for uint256;

    uint256 internal _duration;
    function initialize(
        IERC20Upgradeable token,
        address beneficiary,
        uint256 duration
    ) public initializer {
        __TokenTimelock_init(token, beneficiary, now.add(duration));
        _duration = duration;
    }

    function duration() public view returns (uint256) {
        return _duration;
    }
}
