// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

import './ConfirmedOwner.sol';
import '../vendor/SafeMathChainlink.sol';
import '../interfaces/FlagsInterface.sol';
import '../interfaces/AggregatorV3Interface.sol';
import '../interfaces/UniswapAnchoredView.sol';
import '../interfaces/UpkeepInterface.sol';

/**
 * @notice This validator compares the price of Chainlink aggregators against
 * their equivalent Compound Open Oracle feeds. For each aggregator, a Compound
 * feed is configured with its symbol, number of decimals, and deviation threshold.
 * An aggregator address is flagged when its corresponding Compound feed price deviates
 * by more than the configured threshold from the aggregator price.
 */
contract CompoundPriceFlaggingValidator is ConfirmedOwner, UpkeepInterface {
    using SafeMathChainlink for uint256;

    struct CompoundFeedDetails {
        // Used to call the Compound Open Oracle
        string symbol;
        // Used to convert price to match aggregator decimals
        uint8 decimals;
        // The numerator used to determine the threshold percentage
        // as parts per billion.
        // 1,000,000,000 = 100%
        //   500,000,000 = 50%
        //   100,000,000 = 10%
        //    50,000,000 = 5%
        //    10,000,000 = 1%
        //     2,000,000 = 0.2%
        //                 etc
        uint32 deviationThresholdNumerator;
    }

    uint256 private constant BILLION = 1_000_000_000;

    FlagsInterface private s_flags;
    UniswapAnchoredView private s_compOpenOracle;
    mapping(address => CompoundFeedDetails) private s_feedDetails;

    event CompoundOpenOracleAddressUpdated(
        address indexed from,
        address indexed to
    );
    event FlagsAddressUpdated(address indexed from, address indexed to);
    event FeedDetailsSet(
        address indexed aggregator,
        string symbol,
        uint8 decimals,
        uint32 deviationThresholdNumerator
    );

    constructor(address flagsAddress, address compoundOracleAddress)
        ConfirmedOwner(msg.sender)
    {
        setFlagsAddress(flagsAddress);
        setCompoundOpenOracleAddress(compoundOracleAddress);
    }

    function setCompoundOpenOracleAddress(address oracleAddress)
        public
        onlyOwner()
    {
        address previous = address(s_compOpenOracle);
        if (previous != oracleAddress) {
            s_compOpenOracle = UniswapAnchoredView(oracleAddress);
            emit CompoundOpenOracleAddressUpdated(previous, oracleAddress);
        }
    }

    function setFlagsAddress(address flagsAddress) public onlyOwner() {
        address previous = address(s_flags);
        if (previous != flagsAddress) {
            s_flags = FlagsInterface(flagsAddress);
            emit FlagsAddressUpdated(previous, flagsAddress);
        }
    }

    function setFeedDetails(
        address aggregator,
        string calldata compoundSymbol,
        uint8 compoundDecimals,
        uint32 compoundDeviationThresholdNumerator
    ) public onlyOwner() {
        require(
            compoundDeviationThresholdNumerator > 0 &&
                compoundDeviationThresholdNumerator <= BILLION,
            'Invalid threshold numerator'
        );
        require(
            _compoundPriceOf(compoundSymbol) != 0,
            'Invalid Compound price'
        );
        string memory currentSymbol = s_feedDetails[aggregator].symbol;
        if (bytes(currentSymbol).length == 0) {
            s_feedDetails[aggregator] = CompoundFeedDetails({
                symbol: compoundSymbol,
                decimals: compoundDecimals,
                deviationThresholdNumerator: compoundDeviationThresholdNumerator
            });
            emit FeedDetailsSet(
                aggregator,
                compoundSymbol,
                compoundDecimals,
                compoundDeviationThresholdNumerator
            );
        } else {
            s_feedDetails[aggregator] = CompoundFeedDetails({
                symbol: currentSymbol,
                decimals: compoundDecimals,
                deviationThresholdNumerator: compoundDeviationThresholdNumerator
            });
            emit FeedDetailsSet(
                aggregator,
                currentSymbol,
                compoundDecimals,
                compoundDeviationThresholdNumerator
            );
        }
    }

    function check(address[] memory aggregators)
        public
        view
        returns (address[] memory)
    {
        address[] memory invalidAggregators = new address[](aggregators.length);
        uint256 invalidCount = 0;
        for (uint256 i = 0; i < aggregators.length; i++) {
            address aggregator = aggregators[i];
            if (_isInvalid(aggregator)) {
                invalidAggregators[invalidCount] = aggregator;
                invalidCount++;
            }
        }

        if (aggregators.length != invalidCount) {
            assembly {
                mstore(invalidAggregators, invalidCount)
            }
        }
        return invalidAggregators;
    }

    function update(address[] memory aggregators)
        public
        returns (address[] memory)
    {
        address[] memory invalidAggregators = check(aggregators);
        s_flags.raiseFlags(invalidAggregators);
        return invalidAggregators;
    }

    function checkUpkeep(bytes calldata data)
        external
        override
        view
        returns (bool, bytes memory)
    {
        address[] memory invalidAggregators = check(
            abi.decode(data, (address[]))
        );
        bool needsUpkeep = (invalidAggregators.length > 0);
        return (needsUpkeep, abi.encode(invalidAggregators));
    }

    function performUpkeep(bytes calldata data) external override {
        update(abi.decode(data, (address[])));
    }

    function getFeedDetails(address aggregator)
        public
        view
        returns (
            string memory,
            uint8,
            uint32
        )
    {
        CompoundFeedDetails memory compDetails = s_feedDetails[aggregator];
        return (
            compDetails.symbol,
            compDetails.decimals,
            compDetails.deviationThresholdNumerator
        );
    }

    function flags() external view returns (address) {
        return address(s_flags);
    }

    function compoundOpenOracle() external view returns (address) {
        return address(s_compOpenOracle);
    }

    function _compoundPriceOf(string memory symbol)
        private
        view
        returns (uint256)
    {
        return s_compOpenOracle.price(symbol);
    }

    function _isInvalid(address aggregator)
        private
        view
        returns (bool invalid)
    {
        CompoundFeedDetails memory compDetails = s_feedDetails[aggregator];
        if (compDetails.deviationThresholdNumerator == 0) {
            return false;
        }
        uint256 compPrice = _compoundPriceOf(compDetails.symbol);
        (uint256 aggregatorPrice, uint8 aggregatorDecimals) = _aggregatorValues(
            aggregator
        );

        (aggregatorPrice, compPrice) = _adjustPriceDecimals(
            aggregatorPrice,
            aggregatorDecimals,
            compPrice,
            compDetails.decimals
        );

        return
            _deviatesBeyondThreshold(
                aggregatorPrice,
                compPrice,
                compDetails.deviationThresholdNumerator
            );
    }

    function _aggregatorValues(address aggregator)
        private
        view
        returns (uint256 price, uint8 decimals)
    {
        AggregatorV3Interface priceFeed = AggregatorV3Interface(aggregator);
        (, int256 signedPrice, , , ) = priceFeed.latestRoundData();
        price = uint256(signedPrice);
        decimals = priceFeed.decimals();
    }

    function _adjustPriceDecimals(
        uint256 aggregatorPrice,
        uint8 aggregatorDecimals,
        uint256 compoundPrice,
        uint8 compoundDecimals
    )
        private
        pure
        returns (uint256 adjustedAggregatorPrice, uint256 adjustedCompoundPrice)
    {
        if (aggregatorDecimals > compoundDecimals) {
            uint8 diff = aggregatorDecimals - compoundDecimals;
            uint256 multiplier = 10**uint256(diff);
            compoundPrice = compoundPrice * multiplier;
        } else if (aggregatorDecimals < compoundDecimals) {
            uint8 diff = compoundDecimals - aggregatorDecimals;
            uint256 multiplier = 10**uint256(diff);
            aggregatorPrice = aggregatorPrice * multiplier;
        }
        adjustedAggregatorPrice = aggregatorPrice;
        adjustedCompoundPrice = compoundPrice;
    }

    function _deviatesBeyondThreshold(
        uint256 aggregatorPrice,
        uint256 compPrice,
        uint32 deviationThresholdNumerator
    ) private pure returns (bool beyondThreshold) {
        uint256 deviationAmountThreshold = aggregatorPrice
            .mul(deviationThresholdNumerator)
            .div(BILLION);

        uint256 deviation;
        if (aggregatorPrice > compPrice) {
            deviation = aggregatorPrice.sub(compPrice);
        } else if (aggregatorPrice < compPrice) {
            deviation = compPrice.sub(aggregatorPrice);
        }
        beyondThreshold = (deviation >= deviationAmountThreshold);
    }
}
