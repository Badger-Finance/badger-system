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

def tend_wbtc_eth(badger: BadgerSystem):
    tend_sushi(
        badger=badger,
        strategy_address=WBTC_ETH_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiWbtcEth",
    )


def tend_wbtc_digg(badger: BadgerSystem):
    tend_sushi(
        badger=badger,
        strategy_address=WBTC_DIGG_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiDiggWbtc",
    )


def tend_wbtc_badger(badger: BadgerSystem):
    tend_sushi(
        badger=badger,
        strategy_address=WBTC_BADGER_STRATEGY,
        rewards_price_feed_address=SUSHI_ETH_CHAINLINK,
        key="native.sushiBadgerWbtc",
    )


def tend_sushi(
    badger: BadgerSystem = None,
    strategy_address: str = None,
    rewards_price_feed_address: str = None,
    key: str = None
):
  
    strategy = Contract.from_explorer(strategy_address)
    keeper_address = strategy.keeper()
    pool_id = strategy.pid.call()

    decimals = 18

    claimable_rewards = get_claimable_sushi(
        decimals=decimals, pool_id=pool_id, strategy_address=strategy_address
    )
    console.print(f"claimable rewards: {claimable_rewards}")

    current_price_eth = get_current_price(
        price_feed_address=rewards_price_feed_address, decimals=decimals
    )
    console.print(f"current rewards price per token (ETH): {current_price_eth}")

    gas_fee = estimate_gas_fee(strategy, keeper_address)
    console.print(f"estimated gas fee to tend: {gas_fee}")

    should_tend = is_profitable(claimable_rewards, current_price_eth, gas_fee)
    console.print(f"Should we tend: {should_tend}")

    if should_tend:
        # we should actually take the snapshot and claim here
        snap = SnapshotManager(badger, key)
        before = snap.snap()
        keeper = accounts.at(keeper_address)
        eth_usd_oracle = Contract.from_explorer(ETH_USD_CHAINLINK)
        eth_usd_price = Decimal(eth_usd_oracle.latestRoundData.call()[1] / 10 ** 8)

        if strategy.keeper() == badger.badgerRewardsManager:
            snap.settTendViaManagerAndProcessTx(
                strategy=strategy,
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                tended=claimable_rewards * current_price_eth * eth_usd_price,
            )
        else:
            snap.settTendAndProcessTx(
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                tended=claimable_rewards * current_price_eth * eth_usd_price,
            )


def get_claimable_sushi(
    decimals: int, pool_id: int = None, strategy_address: str = None
) -> Decimal:
    chef = Contract.from_explorer("0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd")
    claimable_rewards = (
        chef.pendingSushi.call(pool_id, strategy_address) / 10 ** decimals
    )
    return Decimal(claimable_rewards)


def get_current_price(price_feed_address: str, decimals: int) -> Decimal:
    price_feed = Contract.from_explorer(price_feed_address)
    return Decimal(price_feed.latestRoundData.call()[1] / 10 ** decimals)


def estimate_gas_fee(strategy: Contract, keeper: str) -> Decimal:
    estimated_gas_to_tend = strategy.tend.estimate_gas({"from": keeper})
    current_gas_price = GasNowStrategy("fast").get_gas_price() / 10 ** 18
    return Decimal(current_gas_price * estimated_gas_to_tend)


def is_profitable(amount: Decimal, price_per: Decimal, gas_fee: Decimal) -> bool:
    fee_percent_of_claim = gas_fee / (amount * price_per)
    console.print(f"Fee as percent of claim: {round(fee_percent_of_claim * 100, 2)}%")
    return (gas_fee / (amount * price_per)) <= 0.01


def main():
    badger = connect_badger(load_keeper=True)
    # skip = keeper_config.get_active_chain_skipped_setts("tend")
    # console.print(badger.getAllSettIds())

    # tend_all(badger, skip)
    console.print("tending wbtc eth")
    tend_wbtc_eth(badger)
    console.print("-------------------")
    console.print("tending wbtc digg")
    tend_wbtc_digg(badger)
    console.print("-------------------")
    console.print("tending wbtc badger")
    tend_wbtc_badger(badger)
