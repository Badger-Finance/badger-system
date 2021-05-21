// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/badger/IController.sol";
import "../BaseStrategy.sol";

/*
    This is a strategy to stabilize Digg with wBTC. It takes advantage of market momentum and accumulated collateral to
    track Digg price with BTC price after rebase events. Users exposed in this strategy are somewhat protected from
    a loss of value due to a negative rebase
    
    Authorized parties include many different parties that can modify trade parameters and fees
*/

interface AggregatorV3Interface {
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}

interface TradeRouter {
    function swapExactETHForTokens(
        uint256,
        address[] calldata,
        address,
        uint256
    ) external payable returns (uint256[] memory);

    function swapExactTokensForTokens(
        uint256,
        uint256,
        address[] calldata,
        address,
        uint256
    ) external returns (uint256[] memory);

    function getAmountsOut(uint256, address[] calldata) external view returns (uint256[] memory); // For a value in, it calculates value out
}

interface UniswapLikeLPToken {
    function sync() external; // We need to call sync before Trading on Uniswap/Sushiswap due to rebase potential of Digg
}

interface DiggTreasury {
    function exchangeWBTCForDigg(
        uint256, // wBTC that we are sending to the treasury exchange
        uint256, // digg that we are requesting from the treasury exchange
        address // address to send the digg to, which is this address
    ) external;
}

contract StabilizeStrategyDiggV1 is BaseStrategy {
    using SafeERC20Upgradeable for ERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // Variables
    uint256 public stabilizeFee; // 1000 = 1%, this fee goes to Stabilize Treasury
    address public diggExchangeTreasury;
    address public stabilizeVault; // Address to the Stabilize treasury

    uint256 public strategyLockedUntil; // The blocknumber that the strategy will prevent withdrawals until
    bool public diggInExpansion;
    uint256 public lastDiggTotalSupply; // The last recorded total supply of the digg token
    uint256 public lastDiggPrice; // The price of Digg at last trade in BTC units
    uint256 public diggSupplyChangeFactor; // This is a factor used by the strategy to determine how much digg to sell in expansion
    uint256 public wbtcSupplyChangeFactor; // This is a factor used by the strategy to determine how much wbtc to sell in contraction
    uint256 public wbtcSellAmplificationFactor; // The higher this number the more aggressive the buyback in contraction
    uint256 public maxGainedDiggSellPercent; // The maximum percent of sellable Digg gains through rebase
    uint256 public maxWBTCSellPercent; // The maximum percent of sellable wBTC;
    uint256 public tradeBatchSize; // The normalized size of the trade batches, can be adjusted
    uint256 public tradeAmountLeft; // The amount left to trade
    uint256 public maxOracleLag; // Maximum amount of lag the oracle can have before reverting the price

    // Constants
    uint256 constant DIVISION_FACTOR = 100000;
    address constant SUSHISWAP_ROUTER_ADDRESS = address(0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F); // Sushi swap router
    address constant UNISWAP_ROUTER_ADDRESS = address(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D);
    address constant SUSHISWAP_DIGG_LP = address(0x9a13867048e01c663ce8Ce2fE0cDAE69Ff9F35E3); // Will need to sync before trading
    address constant UNISWAP_DIGG_LP = address(0xE86204c4eDDd2f70eE00EAd6805f917671F56c52);
    address constant BTC_ORACLE_ADDRESS = address(0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c); // Chainlink BTC Oracle
    address constant DIGG_ORACLE_ADDRESS = address(0x418a6C98CD5B8275955f08F0b8C1c6838c8b1685); // Chainlink DIGG Oracle

    struct TokenInfo {
        ERC20Upgradeable token; // Reference of token
        uint256 decimals; // Decimals of token
    }

    TokenInfo[] private tokenList; // An array of tokens accepted as deposits

    event TradeState(
        uint256 soldAmountNormalized,
        int256 percentPriceChange,
        uint256 soldPercent,
        uint256 oldSupply,
        uint256 newSupply,
        uint256 blocknumber
    );

    event NoTrade(uint256 blocknumber);

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        uint256 _lockedUntil,
        address[2] memory _vaultConfig,
        uint256[4] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        stabilizeVault = _vaultConfig[0];
        diggExchangeTreasury = _vaultConfig[1];

        diggSupplyChangeFactor = 50000; // This is a factor used by the strategy to determine how much digg to sell in expansion
        wbtcSupplyChangeFactor = 20000; // This is a factor used by the strategy to determine how much wbtc to sell in contraction
        wbtcSellAmplificationFactor = 2; // The higher this number the more aggressive the buyback in contraction
        maxGainedDiggSellPercent = 100000; // The maximum percent of sellable Digg gains through rebase
        maxWBTCSellPercent = 50000; // The maximum percent of sellable wBTC;
        tradeBatchSize = 10e18; // The normalized size of the trade batches, can be adjusted
        tradeAmountLeft = 0; // The amount left to trade
        maxOracleLag = 365 days; // Maximum amount of lag the oracle can have before reverting the price

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        stabilizeFee = _feeConfig[3];
        strategyLockedUntil = _lockedUntil; // Deployer can optionally lock strategy from withdrawing until a certain blocknumber

        setupTradeTokens();
        lastDiggPrice = getDiggPrice();
        lastDiggTotalSupply = tokenList[0].token.totalSupply(); // The supply only changes at rebase
        want = address(tokenList[0].token);
    }

    function setupTradeTokens() internal {
        // Start with DIGG
        ERC20Upgradeable _token = ERC20Upgradeable(address(0x798D1bE841a82a273720CE31c822C61a67a601C3));
        tokenList.push(TokenInfo({token: _token, decimals: _token.decimals()}));

        // WBTC
        _token = ERC20Upgradeable(address(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599));
        tokenList.push(TokenInfo({token: _token, decimals: _token.decimals()}));
    }

    function _onlyAnyAuthorizedParties() internal view {
        require(
            msg.sender == strategist || msg.sender == governance || msg.sender == controller || msg.sender == keeper || msg.sender == guardian,
            "Not an authorized party"
        );
    }

    /// ===== View Functions =====

    // Chainlink price grabbers
    function getDiggUSDPrice() public view returns (uint256) {
        AggregatorV3Interface priceOracle = AggregatorV3Interface(DIGG_ORACLE_ADDRESS);
        (, int256 intPrice, , uint256 lastUpdateTime, ) = priceOracle.latestRoundData(); // We only want the answer
        require(block.timestamp.sub(lastUpdateTime) < maxOracleLag, "Price data is too old to use");
        uint256 usdPrice = uint256(intPrice);
        priceOracle = AggregatorV3Interface(BTC_ORACLE_ADDRESS);
        (, intPrice, , lastUpdateTime, ) = priceOracle.latestRoundData(); // We only want the answer
        require(block.timestamp.sub(lastUpdateTime) < maxOracleLag, "Price data is too old to use");
        usdPrice = usdPrice.mul(uint256(intPrice)).mul(10**2);
        return usdPrice; // Digg Price in USD
    }

    function getDiggPrice() public view returns (uint256) {
        AggregatorV3Interface priceOracle = AggregatorV3Interface(DIGG_ORACLE_ADDRESS);
        (, int256 intPrice, , uint256 lastUpdateTime, ) = priceOracle.latestRoundData(); // We only want the answer
        require(block.timestamp.sub(lastUpdateTime) < maxOracleLag, "Price data is too old to use");
        return uint256(intPrice).mul(10**10);
    }

    function getWBTCUSDPrice() public view returns (uint256) {
        AggregatorV3Interface priceOracle = AggregatorV3Interface(BTC_ORACLE_ADDRESS);
        (, int256 intPrice, , uint256 lastUpdateTime, ) = priceOracle.latestRoundData(); // We only want the answer
        require(block.timestamp.sub(lastUpdateTime) < maxOracleLag, "Price data is too old to use");
        return uint256(intPrice).mul(10**10);
    }

    function getTokenAddress(uint256 _id) external view returns (address) {
        require(_id < tokenList.length, "ID is too high");
        return address(tokenList[_id].token);
    }

    function getName() external override pure returns (string memory) {
        return "StabilizeStrategyDiggV1";
    }

    function version() external pure returns (string memory) {
        return "1.0";
    }

    function balanceOf() public override view returns (uint256) {
        // This will return the DIGG and DIGG equivalent of WBTC in Digg decimals
        uint256 _diggAmount = tokenList[0].token.balanceOf(address(this));
        uint256 _wBTCAmount = tokenList[1].token.balanceOf(address(this));
        return _diggAmount.add(wbtcInDiggUnits(_wBTCAmount));
    }

    function wbtcInDiggUnits(uint256 amount) internal view returns (uint256) {
        if (amount == 0) {
            return 0;
        }
        amount = amount.mul(1e18).div(10**tokenList[1].decimals); // Normalize the wBTC amount
        uint256 _digg = amount.mul(getWBTCUSDPrice()).div(1e18); // Get the USD value of wBtC
        _digg = _digg.mul(1e18).div(getDiggUSDPrice());
        _digg = _digg.mul(10**tokenList[0].decimals).div(1e18); // Convert to Digg units
        return _digg;
    }

    function diggInWBTCUnits(uint256 amount) internal view returns (uint256) {
        if (amount == 0) {
            return 0;
        }
        // Converts digg into wbtc equivalent
        amount = amount.mul(1e18).div(10**tokenList[0].decimals); // Normalize the digg amount
        uint256 _wbtc = amount.mul(getDiggUSDPrice()).div(1e18); // Get the USD value of digg
        _wbtc = _wbtc.mul(1e18).div(getWBTCUSDPrice());
        _wbtc = _wbtc.mul(10**tokenList[1].decimals).div(1e18); // Convert to wbtc units
        return _wbtc;
    }

    /// @dev Not used
    function balanceOfPool() public override view returns (uint256) {
        return 0;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](2);
        protectedTokens[0] = address(tokenList[0].token);
        protectedTokens[1] = address(tokenList[1].token);
        return protectedTokens;
    }

    // Customer active Strategy functions

    // This function will sell one token for another on Sushiswap and Uniswap
    function exchange(
        uint256 _inID,
        uint256 _outID,
        uint256 _amount
    ) internal {
        address _inputToken = address(tokenList[_inID].token);
        address _outputToken = address(tokenList[_outID].token);
        // One route, between DIGG and WBTC on Sushiswap and Uniswap, split based on liquidity of LPs
        address[] memory path = new address[](2);
        path[0] = _inputToken;
        path[1] = _outputToken;

        // Sync Sushiswap pool
        UniswapLikeLPToken lpPool = UniswapLikeLPToken(SUSHISWAP_DIGG_LP);
        lpPool.sync(); // Sync the pool amounts
        // Sync Uniswap pool
        lpPool = UniswapLikeLPToken(UNISWAP_DIGG_LP);
        lpPool.sync(); // Sync the pool amounts

        // Now determine the split between Uni and Sushi
        // Amount sold is split between these two biggest liquidity providers to decrease the chance of price inequities between the exchanges
        // This also helps reduce slippage and creates a higher return than using one exchange
        // Look at the total balance of the pooled tokens in Uniswap compared to the total for both exchanges
        uint256 uniPercent = tokenList[0]
            .token
            .balanceOf(address(UNISWAP_DIGG_LP))
            .add(tokenList[1].token.balanceOf(address(UNISWAP_DIGG_LP)))
            .mul(DIVISION_FACTOR)
            .div(
            tokenList[0]
                .token
                .balanceOf(address(UNISWAP_DIGG_LP))
                .add(tokenList[0].token.balanceOf(address(SUSHISWAP_DIGG_LP)))
                .add(tokenList[1].token.balanceOf(address(UNISWAP_DIGG_LP)))
                .add(tokenList[1].token.balanceOf(address(SUSHISWAP_DIGG_LP)))
        );
        uint256 uniAmount = _amount.mul(uniPercent).div(DIVISION_FACTOR);
        _amount = _amount.sub(uniAmount);

        // Make sure selling produces a growth in pooled tokens
        TradeRouter router = TradeRouter(SUSHISWAP_ROUTER_ADDRESS);
        uint256 minAmount = _amount.mul(10**tokenList[_outID].decimals).div(10**tokenList[_inID].decimals); // Trades should always increase balance
        uint256[] memory estimates = router.getAmountsOut(_amount, path);
        uint256 estimate = estimates[estimates.length - 1]; // This is the amount of expected output token
        if (estimate > minAmount) {
            _safeApproveHelper(_inputToken, SUSHISWAP_ROUTER_ADDRESS, _amount);
            router.swapExactTokensForTokens(_amount, minAmount, path, address(this), now.add(60)); // Get output token
        }

        if (uniAmount > 0) {
            // Now try the same on Uniswap
            router = TradeRouter(UNISWAP_ROUTER_ADDRESS);
            minAmount = uniAmount.mul(10**tokenList[_outID].decimals).div(10**tokenList[_inID].decimals); // Trades should always increase balance
            estimates = router.getAmountsOut(uniAmount, path);
            estimate = estimates[estimates.length - 1]; // This is the amount of expected output token
            if (estimate > minAmount) {
                _safeApproveHelper(_inputToken, UNISWAP_ROUTER_ADDRESS, uniAmount);
                router.swapExactTokensForTokens(uniAmount, minAmount, path, address(this), now.add(60)); // Get output token
            }
        }
        return;
    }

    function governancePullSomeCollateral(uint256 _amount) external {
        // This will pull wBTC from the contract by governance
        _onlyGovernance();
        ERC20Upgradeable wbtc = tokenList[1].token;
        uint256 _balance = wbtc.balanceOf(address(this));
        if (_amount <= _balance) {
            wbtc.safeTransfer(governance, _amount);
        }
    }

    // Changeable variables by governance
    function setTradingBatchSize(uint256 _size) external {
        _onlyGovernance();
        tradeBatchSize = _size;
    }

    function setOracleLagTime(uint256 _time) external {
        _onlyAnyAuthorizedParties();
        maxOracleLag = _time;
    }

    function setStabilizeFee(uint256 _fee) external {
        _onlyGovernance();
        require(_fee <= MAX_FEE, "base-strategy/excessive-stabilize-fee");
        stabilizeFee = _fee;
    }

    function setStabilizeVault(address _vault) external {
        _onlyGovernance();
        require(_vault != address(0), "No vault");
        stabilizeVault = _vault;
    }

    function setDiggExchangeTreasury(address _treasury) external {
        _onlyGovernance();
        require(_treasury != address(0), "No vault");
        diggExchangeTreasury = _treasury;
    }

    function setSellFactorsAndPercents(
        uint256 _dFactor, // This will influence how much digg is sold when the token is in expansion
        uint256 _wFactor, // This will influence how much wbtc is sold when the token is in contraction
        uint256 _wAmplifier, // This will amply the amount of wbtc sold based on the change in the price
        uint256 _mPDigg, // Governance can cap maximum amount of gained digg sold during rebase. 0-100% accepted (0-100000)
        uint256 _mPWBTC // Governance can cap the maximum amount of wbtc sold during rebase. 0-100% accepted (0-100000)
    ) external {
        _onlyGovernanceOrStrategist();
        require(_mPDigg <= 100000 && _mPWBTC <= 100000, "Percents outside range");
        diggSupplyChangeFactor = _dFactor;
        wbtcSupplyChangeFactor = _wFactor;
        wbtcSellAmplificationFactor = _wAmplifier;
        maxGainedDiggSellPercent = _mPDigg;
        maxWBTCSellPercent = _mPWBTC;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(tokenList[0].token) != _asset, "DIGG");
        require(address(tokenList[1].token) != _asset, "WBTC");
    }

    /// @notice No active position
    function _deposit(uint256 _want) internal override {
        // This strategy doesn't do anything when tokens are deposited
    }

    /// @dev No active position to exit, just send all want to controller as per wrapper withdrawAll() function
    function _withdrawAll() internal override {
        // This strategy doesn't do anything when tokens are withdrawn, wBTC stays in strategy until governance decides
        // what to do with it
        // When a user withdraws, it is performed via _withdrawSome
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        require(block.number >= strategyLockedUntil, "Unable to withdraw from strategy until certain block");
        // We only have idle DIGG, withdraw from the strategy directly
        // Note: This value is in DIGG fragments

        // Make sure that when the user withdraws, the vaults try to maintain a 1:1 ratio in value
        uint256 _diggEquivalent = wbtcInDiggUnits(tokenList[1].token.balanceOf(address(this)));
        uint256 _diggBalance = tokenList[0].token.balanceOf(address(this));
        uint256 _extraDiggNeeded = 0;
        if (_amount > _diggBalance) {
            _extraDiggNeeded = _amount.sub(_diggBalance);
            _diggBalance = 0;
        } else {
            _diggBalance = _diggBalance.sub(_amount);
        }

        if (_extraDiggNeeded > 0) {
            // Calculate how much digg we need from digg vault
            _diggEquivalent = _diggEquivalent.sub(_extraDiggNeeded);
        }

        if (_diggBalance < _diggEquivalent || _diggEquivalent == 0) {
            // Now balance the vaults
            _extraDiggNeeded = _extraDiggNeeded.add(_diggEquivalent.sub(_diggBalance).div(2));
            // Exchange with the digg treasury to keep this balanced
            uint256 wbtcAmount = diggInWBTCUnits(_extraDiggNeeded);
            if (wbtcAmount > tokenList[1].token.balanceOf(address(this))) {
                wbtcAmount = tokenList[1].token.balanceOf(address(this)); // Make sure we can actual spend it
                _extraDiggNeeded = wbtcInDiggUnits(wbtcAmount);
            }
            _safeApproveHelper(address(tokenList[1].token), diggExchangeTreasury, wbtcAmount);
            // TODO: Badger team needs to develop a contract that holds Digg, can pull wbtc from this contract and return the requested amount of Digg to this address
            DiggTreasury(diggExchangeTreasury).exchangeWBTCForDigg(wbtcAmount, _extraDiggNeeded, address(this)); // Internal no slip treasury exchange
        }

        return _amount;
    }

    // We will separate trades into batches to reduce market slippage
    // Keepers can call this function after rebalancing to sell/buy slowly
    function executeTradeBatch() public whenNotPaused {
        _onlyAuthorizedActors();
        if (tradeAmountLeft == 0) {
            return;
        }

        // Reduce the trade amount left
        uint256 batchSize = tradeBatchSize;
        if (tradeAmountLeft < batchSize) {
            batchSize = tradeAmountLeft;
        }
        tradeAmountLeft = tradeAmountLeft.sub(batchSize);

        if (diggInExpansion == true) {
            // We will be selling digg for wbtc, convert to digg units from normalized
            batchSize = batchSize.mul(10**tokenList[0].decimals).div(1e18);
            uint256 _earned = tokenList[1].token.balanceOf(address(this)); // Get the pre-exchange WBTC balance
            if (batchSize > 0) {
                exchange(0, 1, batchSize); // Sell Digg for wBTC
            }
            _earned = tokenList[1].token.balanceOf(address(this)).sub(_earned);

            if (_earned > 0) {
                // We will distribute some of this wBTC to different parties
                _processFee(address(tokenList[1].token), _earned, performanceFeeGovernance, IController(controller).rewards());
                _processFee(address(tokenList[1].token), _earned, stabilizeFee, stabilizeVault);
            }
        } else {
            // We will be selling wbtc for digg, convert to wbtc units from normalized
            batchSize = batchSize.mul(10**tokenList[1].decimals).div(1e18);
            uint256 _earned = tokenList[0].token.balanceOf(address(this)); // Get the pre-exchange Digg balance
            if (batchSize > 0) {
                exchange(1, 0, batchSize); // Sell WBTC for digg
            }
            _earned = tokenList[0].token.balanceOf(address(this)).sub(_earned);
        }
    }

    function rebalance() external whenNotPaused {
        // Modified the harvest function and called it rebalance
        // This function is called by Keepers post rebase to evaluate what to do with the trade
        // A percent of wbtc earned during expansion goes to rewards pool and stabilize vault
        _onlyAuthorizedActors();
        uint256 currentTotalSupply = tokenList[0].token.totalSupply();
        if (currentTotalSupply != lastDiggTotalSupply) {
            // Rebase has taken place, act on it
            int256 currentPrice = int256(getDiggPrice());
            int256 percentChange = ((currentPrice - int256(lastDiggPrice)) * int256(DIVISION_FACTOR)) / int256(lastDiggPrice);
            if (percentChange > 100000) {
                percentChange = 100000;
            } // We only act on at most 100% change
            if (percentChange < -100000) {
                percentChange = -100000;
            }
            if (currentTotalSupply > lastDiggTotalSupply) {
                diggInExpansion = true;
                // Price is still positive
                // We will sell digg for wbtc

                // Our formula to calculate the amount of digg sold is below
                // digg_supply_change_amount * (digg_supply_change_factor - price_change_percent)
                // If amount is < 0, nothing is sold. The higher the price change, the less is sold
                uint256 sellPercent;
                if (int256(diggSupplyChangeFactor) <= percentChange) {
                    sellPercent = 0;
                } else if (percentChange > 0) {
                    sellPercent = diggSupplyChangeFactor.sub(uint256(percentChange));
                } else {
                    sellPercent = diggSupplyChangeFactor.add(uint256(-percentChange));
                }
                if (sellPercent > maxGainedDiggSellPercent) {
                    sellPercent = maxGainedDiggSellPercent;
                }

                // Get the percentage amount the supply increased by
                uint256 changedDigg = currentTotalSupply.sub(lastDiggTotalSupply).mul(DIVISION_FACTOR).div(lastDiggTotalSupply);
                changedDigg = tokenList[0].token.balanceOf(address(this)).mul(changedDigg).div(DIVISION_FACTOR);
                // This is the amount of Digg gain from the rebase returned

                uint256 _amount = changedDigg.mul(sellPercent).div(DIVISION_FACTOR); // This the amount to sell

                // Normalize sell amount
                _amount = _amount.mul(1e18).div(10**tokenList[0].decimals);
                tradeAmountLeft = _amount;
                executeTradeBatch(); // This will start to trade in batches

                emit TradeState(_amount, percentChange, sellPercent, lastDiggTotalSupply, currentTotalSupply, block.number);
            } else {
                diggInExpansion = false;
                // Price is now negative
                // We will sell wbtc for digg only if price begins to rise again
                if (percentChange > 0) {
                    // Our formula to calculate the percentage of wbtc sold is below
                    // -digg_supply_change_percent * (wbtc_supply_change_factor + price_change_percent * amplication_factor)

                    // First get the digg supply change in positive units
                    uint256 changedDiggPercent = lastDiggTotalSupply.sub(currentTotalSupply).mul(DIVISION_FACTOR).div(lastDiggTotalSupply);

                    // The faster the rise and the larger the negative rebase, the more that is bought
                    uint256 sellPercent = changedDiggPercent
                        .mul(wbtcSupplyChangeFactor.add(uint256(percentChange).mul(wbtcSellAmplificationFactor)))
                        .div(DIVISION_FACTOR);
                    if (sellPercent > maxWBTCSellPercent) {
                        sellPercent = maxWBTCSellPercent;
                    }

                    // We just sell this percentage of wbtc for digg gains
                    uint256 _amount = tokenList[1].token.balanceOf(address(this)).mul(sellPercent).div(DIVISION_FACTOR);

                    //Normalize the amount
                    _amount = _amount.mul(1e18).div(10**tokenList[1].decimals);
                    tradeAmountLeft = _amount;
                    executeTradeBatch();

                    emit TradeState(_amount, percentChange, sellPercent, lastDiggTotalSupply, currentTotalSupply, block.number);
                } else {
                    tradeAmountLeft = 0; // Do not trade
                    emit NoTrade(block.number);
                }
            }
            lastDiggPrice = uint256(currentPrice);
            lastDiggTotalSupply = currentTotalSupply;
        } else {
            emit NoTrade(block.number);
        }
    }
}
