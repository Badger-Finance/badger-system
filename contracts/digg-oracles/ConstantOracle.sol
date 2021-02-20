//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.8;

import "interfaces/digg/IMedianOracle.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/* 
    ===== Constant "Always 1" Oracle =====
    On-chain data source that always pushes the value representing one to the specified Oracle.
    Intended for use with the DIGG CPI Oracle, which is effectively unused, always returning 1.
*/
contract ConstantOracle is OwnableUpgradeable {
    IMedianOracle internal _medianOracle;

    event UpdatePushed(IMedianOracle medianOracle, uint256 value);

    constructor(IMedianOracle medianOracle) public {
        __Ownable_init();
        _medianOracle = medianOracle;
    }

    function updateAndPush() external onlyOwner {
        _medianOracle.pushReport(1 ether);
        emit UpdatePushed(_medianOracle, 1 ether);
    }

    function medianOracle() external view returns (IMedianOracle) {
        return _medianOracle;
    }
}
