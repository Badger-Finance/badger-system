//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/TokenTimelockUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "interfaces/aragon/IVoting.sol";

contract SimpleTimelockWithVoting is TokenTimelockUpgradeable {
    using SafeMathUpgradeable for uint256;

    function initialize(
        IERC20Upgradeable token,
        address beneficiary,
        uint256 releaseTime
    ) public initializer {
        __TokenTimelock_init(token, beneficiary, releaseTime);
    }

    function release(uint256 amount) public {
        // solhint-disable-next-line not-rely-on-time
        require(block.timestamp >= releaseTime(), "TokenTimelock: current time is before release time");

        address recipient = 0xB65cef03b9B89f99517643226d76e286ee999e77;
        require(msg.sender == 0xB65cef03b9B89f99517643226d76e286ee999e77);

        token().safeTransfer(recipient, amount);
    }

    function vote(
        uint256 _voteId,
        bool _supports,
        bool _executesIfDecided
    ) external payable {
        require(msg.sender == 0xB65cef03b9B89f99517643226d76e286ee999e77);

        IERC20Upgradeable badger = IERC20Upgradeable(0x3472A5A71965499acd81997a54BBA8D852C6E53d);
        uint256 preAmount = badger.balanceOf(address(this));

        IVoting(0xDc344bFB12522bF3fa58EF0d6b9a41256fc79A1b).vote(_voteId, _supports, _executesIfDecided);

        uint256 postAmount = badger.balanceOf(address(this));
        require(postAmount >= preAmount, "smart-vesting/locked-balance-check");
    }
}
