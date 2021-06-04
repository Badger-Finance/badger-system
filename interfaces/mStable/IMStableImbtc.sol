// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.9.0;

import {IERC20} from "../erc20/IERC20.sol";

abstract contract IMStableImbtc is IERC20 {
    function depositSavings(uint256 _amount) external virtual returns (uint256 creditsIssued);
}
