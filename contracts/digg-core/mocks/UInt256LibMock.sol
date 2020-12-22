pragma solidity 0.4.24;

import "interfaces/digg/IMock.sol";
import "../lib/UInt256Lib.sol";


contract UInt256LibMock is IMock {
    function toInt256Safe(uint256 a)
        external
        returns (int256)
    {
        int256 result = UInt256Lib.toInt256Safe(a);
        emit ReturnValueInt256(result);
        return result;
    }
}
