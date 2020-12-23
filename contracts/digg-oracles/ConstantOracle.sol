//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.8;

import "interfaces/digg/IMedianOracle.sol";

/* On-chain oracle data source that always push a constant value specified on creation */
contract ConstantOracle {
  uint256 internal _value;
  IMedianOracle internal _medianOracle;

  event UpdatePushed(IMedianOracle medianOracle, uint256 value);

  constructor(uint256 value, IMedianOracle medianOracle) public {
    _value = value;
    _medianOracle = medianOracle;
  }

  function updateAndPush() external {
    _medianOracle.pushReport(_value);
    emit UpdatePushed(_medianOracle, _value);
  }

  function value() external view returns(uint256) {
    return _value;
  }

  function medianOracle() external view returns(IMedianOracle) {
    return _medianOracle;
  }
}
