from helpers.sett.SnapshotManager import SnapshotManager
from config.keeper import keeper_config
from helpers.utils import tx_wait, val
from brownie import *
from helpers.gas_utils import gas_strategies
from brownie.network.gas.strategies import (
    GasNowStrategy,
    ExponentialScalingStrategy,
    SimpleGasStrategy,
)
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from decimal import Decimal

gas_strategies.set_default_for_active_chain()

console = Console()

ETH_USD_CHAINLINK = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
SUSHI_ETH_CHAINLINK = "0xe572CeF69f43c2E488b33924AF04BDacE19079cf"
WBTC_ETH_STRATEGY = "0x7A56d65254705B4Def63c68488C0182968C452ce"
WBTC_DIGG_STRATEGY = "0xaa8dddfe7DFA3C3269f1910d89E4413dD006D08a"
WBTC_BADGER_STRATEGY = "0x3a494D79AA78118795daad8AeFF5825C6c8dF7F1"


def harvest_wbtc_eth(badger: BadgerSystem = None):
    harvest_sushi(
        badger=badger,
        strategy_address=WBTC_ETH_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiWbtcEth",
    )


def harvest_wbtc_digg(badger: BadgerSystem = None):
    harvest_sushi(
        badger=badger,
        strategy_address=WBTC_DIGG_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiDiggWbtc",
    )


def harvest_wbtc_badger(badger: BadgerSystem = None):
    harvest_sushi(
        badger=badger,
        strategy_address=WBTC_BADGER_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiBadgerWbtc",
    )


def harvest_sushi(
    badger: BadgerSystem = None,
    strategy_address: str = None,
    rewards_price_feed_address: str = None,
    key: str = None,
):
    strategy = Contract.from_explorer(strategy_address)
    keeper_address = strategy.keeper.call()
    pool_id = strategy.pid.call()

    xsushi = Contract.from_explorer("0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272")
    sushi = Contract.from_explorer(xsushi.sushi.call())

    decimals = 18

    claimable_rewards = get_harvestable_xsushi(
        decimals=decimals,
        pool_id=pool_id,
        strategy_address=strategy_address,
        xsushi=xsushi,
    )
    console.print(f"claimable rewards: {claimable_rewards}")

    current_price_eth = get_current_price(
        price_feed_address=rewards_price_feed_address,
        decimals=decimals,
        xsushi=xsushi,
        sushi=sushi,
    )
    console.print(f"current rewards price per token (ETH): {current_price_eth}")

    gas_fee = estimate_gas_fee(strategy, keeper_address)
    console.print(f"estimated gas fee to harvest: {gas_fee}")

    should_harvest = is_profitable(claimable_rewards, current_price_eth, gas_fee)
    console.print(f"Should we harvest: {should_harvest}")

    if should_harvest and badger:
        # we should actually take the snapshot and claim here
        snap = SnapshotManager(badger, key)
        before = snap.snap()
        keeper = accounts.at(keeper_address)
        eth_usd_oracle = Contract.from_explorer(ETH_USD_CHAINLINK)
        eth_usd_price = Decimal(eth_usd_oracle.latestRoundData.call()[1] / 10 ** 8)

        if strategy.keeper() == badger.badgerRewardsManager:
            snap.settHarvestViaManagerAndProcessTx(
                strategy=strategy,
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                harvested=claimable_rewards * current_price_eth * eth_usd_price,
            )
        else:
            snap.settHarvestAndProcessTx(
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                harvested=claimable_rewards * current_price_eth * eth_usd_price,
            )


def get_harvestable_xsushi(
    decimals: int,
    pool_id: int = None,
    strategy_address: str = None,
    xsushi: Contract = None,
) -> Decimal:
    harvestable_amt = xsushi.balanceOf.call(strategy_address) / 10 ** decimals
    return Decimal(harvestable_amt)


def get_current_price(
    price_feed_address: str,
    decimals: int,
    xsushi: Contract = None,
    sushi: Contract = None,
) -> Decimal:
    price_feed = Contract.from_explorer(price_feed_address)
    ratio = sushi.balanceOf.call(xsushi.address) / xsushi.totalSupply.call()
    return Decimal((price_feed.latestRoundData.call()[1] / 10 ** decimals) * ratio)


def estimate_gas_fee(strategy: Contract, keeper: str) -> Decimal:
    estimated_gas_to_harvest = strategy.harvest.estimate_gas({"from": keeper})
    current_gas_price = GasNowStrategy("fast").get_gas_price() / 10 ** 18
    return Decimal(current_gas_price * estimated_gas_to_harvest)


def is_profitable(amount: Decimal, price_per: Decimal, gas_fee: Decimal) -> bool:
    fee_percent_of_claim = (
        1 if amount * price_per == 0 else gas_fee / (amount * price_per)
    )
    console.print(f"Fee as percent of harvest: {round(fee_percent_of_claim * 100, 2)}%")
    return fee_percent_of_claim <= 0.05


def main():
    badger = connect_badger(load_keeper=True)
    # skip = keeper_config.get_active_chain_skipped_setts("harvest")
    # console.print(badger.getAllSettIds())

    # harvest_all(badger, skip)

    console.print("harvesting wbtc eth")
    harvest_wbtc_eth(badger=badger)
    console.print("-------------------")
    console.print("harvesting wbtc digg")
    harvest_wbtc_digg(badger=badger)
    console.print("-------------------")
    console.print("harvesting wbtc badger")
    harvest_wbtc_badger(badger=badger)
