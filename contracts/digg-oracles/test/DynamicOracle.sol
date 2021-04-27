//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.8;

import "interfaces/digg/IMedianOracle.sol";

/* On-chain oracle data source that pushes an explicitly set value at runtime via set and push API.
   This is used strictly for TEST PURPOSES ONLY to allow us to control the feed to the market median oracle.
*/
contract DynamicOracle {
    IMedianOracle internal _medianOracle;

    event UpdatePushed(IMedianOracle medianOracle, uint256 value);

    constructor(IMedianOracle medianOracle) public {
        _medianOracle = medianOracle;
    }

    function pushReport(uint256 value) external returns (uint256) {
        _medianOracle.pushReport(value);
        emit UpdatePushed(_medianOracle, value);
        return value;
    }

    function medianOracle() external view returns (IMedianOracle) {
        return _medianOracle;
    }
}
