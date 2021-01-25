//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.8;

import "interfaces/digg/IMedianOracle.sol";

/* On-chain oracle data source that pushes an explicitly set value at runtime via set and push API.
   This is used strictly for TEST PURPOSES ONLY to allow us to control the feed to the market median oracle.
*/
contract DynamicOracle {
    uint256 internal _value;
    IMedianOracle internal _medianOracle;

    uint256 private constant DECIMALS = 18;

    event UpdatePushed(IMedianOracle medianOracle, uint256 value);

    constructor(IMedianOracle medianOracle) public {
        // Starts at 1 for testing, this value is not pushed
        // as the set and push api needs to be called.
        _value = 10**DECIMALS;
        _medianOracle = medianOracle;
    }

    /**
     * @notice Sets a value and pushes to median oracle.
     * @param value is expected to be 18 decimal fixed point number.
     */
    function setValueAndPush(uint256 value) external returns (uint256) {
        _value = value;
        _medianOracle.pushReport(_value);
        return _value;
    }

    function medianOracle() external view returns (IMedianOracle) {
        return _medianOracle;
    }
}
