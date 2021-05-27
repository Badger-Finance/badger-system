// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.9.0;

import {IERC20} from "../erc20/IERC20.sol";

abstract contract IMStableAsset is IERC20 {
    function mint(
        address _input,
        uint256 _inputQuantity,
        uint256 _minOutputQuantity,
        address _recipient
    ) external virtual returns (uint256 mintOutput);

    function getMintOutput(address _input, uint256 _inputQuantity) external virtual view returns (uint256 mintOutput);
}
