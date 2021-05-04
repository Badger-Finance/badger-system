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

CRV_USD_CHAINLINK = "0xCd627aA160A6fA45Eb793D19Ef54f5062F20f33f"
CRV_ETH_CHAINLINK = "0x8a12Be339B0cD1829b91Adc01977caa5E9ac121e"
REN_CRV_STRATEGY = "0x444B860128B7Bf8C0e864bDc3b7a36a940db7D88"
SBTC_CRV_STRATEGY = "0x3Efc97A8e23f463e71Bf28Eb19690d097797eb17"
TBTC_CRV_STRATEGY = "0xE2fA197eAA5C726426003074147a08beaA59403B"

XSUSHI_TOKEN = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"


def harvest_ren_crv(badger: BadgerSystem = None):
    harvest(
        badger=badger,
        strategy_address=REN_CRV_STRATEGY,
        rewards_price_feed_address=CRV_ETH_CHAINLINK,
        key="native.renCrv",
    )


def harvest_sbtc_crv(badger: BadgerSystem = None):
    harvest(
        badger=badger,
        strategy_address=SBTC_CRV_STRATEGY,
        rewards_price_feed_address=CRV_ETH_CHAINLINK,
        key="native.sbtcCrv",
    )


def harvest_tbtc_crv(badger: BadgerSystem = None):
    harvest(
        badger=badger,
        strategy_address=TBTC_CRV_STRATEGY,
        rewards_price_feed_address=CRV_ETH_CHAINLINK,
        key="native.tbtcCrv",
    )


def harvest(
    badger: BadgerSystem = None,
    strategy_address: str = None,
    rewards_price_feed_address: str = None,
    key: str = None,
):
    strategy = Contract.from_explorer(strategy_address)
    keeper_address = strategy.keeper.call()

    crv = Contract.from_explorer(strategy.crv.call())
    gauge = Contract.from_explorer(strategy.gauge())

    decimals = 18

    claimable_rewards = get_harvestable_amount(
        decimals=crv.decimals(),
        strategy=strategy,
        gauge=gauge,
    )
    console.print(f"claimable rewards: {claimable_rewards}")

    current_price_eth = get_current_price(
        price_feed_address=rewards_price_feed_address,
        decimals=crv.decimals()
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
        crv_usd_oracle = Contract.from_explorer(CRV_USD_CHAINLINK)
        crv_usd_price = Decimal(crv_usd_oracle.latestRoundData.call()[1] / 10 ** 8)

        if strategy.keeper() == badger.badgerRewardsManager:
            snap.settHarvestViaManagerAndProcessTx(
                strategy=strategy,
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                harvested=claimable_rewards * crv_usd_price,
            )
        else:
            snap.settHarvestAndProcessTx(
                overrides={"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
                harvested=claimable_rewards * crv_usd_price,
            )


def get_harvestable_amount(
    decimals: int,
    strategy: Contract = None,
    gauge: Contract = None
) -> Decimal:
    harvestable_amt = gauge.claimable_tokens.call(strategy.address) / 10 ** decimals
    return Decimal(harvestable_amt)


def get_current_price(
    price_feed_address: str,
    decimals: int,
) -> Decimal:
    price_feed = Contract.from_explorer(price_feed_address)
    return Decimal(price_feed.latestRoundData.call()[1] / 10 ** decimals)


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

    console.print("harvesting ren crv")
    harvest_ren_crv(badger=badger)
    console.print("-------------------")
    console.print("harvesting sbtc crv")
    harvest_sbtc_crv(badger=badger)
    console.print("-------------------")
    console.print("harvesting tbtc crv")
    harvest_tbtc_crv(badger=badger)
