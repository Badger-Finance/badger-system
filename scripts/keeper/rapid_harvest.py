from assistant.rewards.rewards_checker import val
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from config.active_emissions import get_active_rewards_schedule
from helpers.console_utils import console
from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.snapshot import diff_numbers_by_key, snap_strategy_balance
from helpers.utils import shares_to_fragments, to_digg_shares, to_tabulate, tx_wait
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.digg_system import connect_digg
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from tabulate import tabulate

gas_strategies.set_default_for_active_chain()

uniswap = UniswapSystem()
sushiswap = SushiswapSystem()


def transfer_for_strategy(badger: BadgerSystem, key, amount, decimals=18):
    console.print(
        "Transferring Amount for Strategy {}".format(key), val(amount, decimals)
    )
    manager = badger.badgerRewardsManager
    strategy = badger.getStrategy(key)

    before = snap_strategy_balance(badger, key, manager)

    transfer_for_strategy_internal(badger, key, amount)

    after = snap_strategy_balance(badger, key, manager)
    diff = diff_numbers_by_key(before, after)

    console.print("[green]==Transfer for {}==[/green]".format(key))
    to_tabulate("Diff {}".format(key), diff)


def transfer_for_strategy_internal(badger, key, amount):
    digg = badger.digg
    strategy = badger.getStrategy(key)
    manager = badger.badgerRewardsManager
    want = interface.IERC20(strategy.want())
    manager.transferWant(
        want, strategy, amount, {"from": badger.keeper, "gas_limit": 1000000}
    )


def rapid_harvest(badger):
    """
    Atomically transfer and deposit tokens from rewards manager to associated strategies
    Requires that LP positons are swapped
    """

    # TODO: Output message when failure
    # TODO: Use test mode if RPC active, no otherwise

    rewards = get_active_rewards_schedule(badger)
    digg = badger.digg
    manager = badger.badgerRewardsManager

    if rpc.is_active():
        """
        Test: Load up sending accounts with ETH and whale tokens
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    # TODO: Daily amount = calculate from the LP token scale

    # # ===== native.uniBadgerWbtc =====
    key = "native.uniBadgerWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.sushiBadgerWbtc =====
    key = "native.sushiBadgerWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.uniDiggWbtc =====
    key = "native.uniDiggWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.sushiDiggWbtc =====
    key = "native.sushiDiggWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # ===== native.badger =====
    key = "native.badger"
    # TODO: Specify actual amounts here
    transfer_for_strategy(
        badger, key, rewards.getDistributions(key).getToStakingRewardsDaily("badger")
    )

    # ===== native.digg =====
    key = "native.digg"
    diggBaseRewards = shares_to_fragments(
        rewards.getDistributions(key).getToStakingRewardsDaily("digg")
    )
    transfer_for_strategy(
        badger, key, diggBaseRewards, decimals=9,
    )


def main():
    badger = connect_badger(load_keeper=True)
    rapid_harvest(badger)
