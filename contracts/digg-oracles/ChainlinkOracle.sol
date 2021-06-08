pragma solidity ^0.6.7;

import "interfaces/chainlink/AggregatorV3Interface.sol";
import "interfaces/digg/IMedianOracle.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

contract ChainlinkOracle is OwnableUpgradeable {
    AggregatorV3Interface internal priceFeed;

    event UpdatePushed(IMedianOracle medianOracle, uint256 price);

    IMedianOracle internal _medianOracle;

    /**
     * Network: Ethereum
     * Aggregator: DIGG/BTC
     * Address: 0x418a6C98CD5B8275955f08F0b8C1c6838c8b1685
     */
    constructor(IMedianOracle medianOracle) public {
        __Ownable_init();
        uint256 decimals = 18;
        _medianOracle = medianOracle;
        priceFeed = AggregatorV3Interface(0x418a6C98CD5B8275955f08F0b8C1c6838c8b1685);
    }

    /**
     * Returns the latest price
     */
    function getThePrice() public returns (int256) {
        (uint80 roundID, int256 price, uint256 startedAt, uint256 timeStamp, uint80 answeredInRound) = priceFeed.latestRoundData();
        price = price * (10**10);
        _medianOracle.pushReport(uint256(price));
        emit UpdatePushed(_medianOracle, uint256(price));
        return price;
    }
}