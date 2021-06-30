from assistant.rewards.rewards_checker import val
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from config.active_emissions import get_active_rewards_schedule
from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.snapshot import diff_numbers_by_key, snap_strategy_balance
from helpers.utils import shares_to_fragments, to_digg_shares, to_tabulate, tx_wait
from rich.console import Console
from scripts.keeper.rapid_harvest import rapid_harvest
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.digg_system import connect_digg
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from tabulate import tabulate

gas_strategies.set_default_for_active_chain()

uniswap = UniswapSystem()
sushiswap = SushiswapSystem()

console = Console()

wbtc = interface.IERC20(registry.tokens.wbtc)


def lp_for_strategy(badger: BadgerSystem, key):
    """
    Add maximum liquidity for associated strategy LP position
    """
    manager = badger.badgerRewardsManager
    strategy = badger.getStrategy(key)

    want = interface.IERC20(strategy.want())

    before = snap_strategy_balance(badger, key, manager)

    lp_for_strategy_internal(badger, key)

    after = snap_strategy_balance(badger, key, manager)
    diff = diff_numbers_by_key(before, after)

    console.print("[cyan]==LP for {}==[/cyan]".format(key))
    to_tabulate("Diff {}".format(key), diff)


def lp_for_strategy_internal(badger, key):
    digg = badger.digg
    manager = badger.badgerRewardsManager
    if key == "native.uniBadgerWbtc":
        manager.addLiquidityUniswap(
            badger.token, wbtc, {"from": badger.keeper, "gas_limit": 1000000}
        )
    if key == "native.sushiBadgerWbtc":
        manager.addLiquiditySushiswap(
            badger.token, wbtc, {"from": badger.keeper, "gas_limit": 1000000}
        )
    if key == "native.uniDiggWbtc":
        manager.addLiquidityUniswap(
            digg.token, wbtc, {"from": badger.keeper, "gas_limit": 1000000}
        )
    if key == "native.sushiDiggWbtc":
        manager.addLiquiditySushiswap(
            digg.token, wbtc, {"from": badger.keeper, "gas_limit": 1000000}
        )


def swap_for_strategy(badger: BadgerSystem, key, amount):
    manager = badger.badgerRewardsManager
    print(key)
    strategy = badger.getStrategy(key)

    before = snap_strategy_balance(badger, key, manager)

    swap_for_strategy_internal(badger, key, amount)

    after = snap_strategy_balance(badger, key, manager)
    diff = diff_numbers_by_key(before, after)

    console.print("[green]==Swap for {}==[/green]".format(key))
    console.print("Amount", amount)
    to_tabulate("Diff {}".format(key), diff)


def swap_for_strategy_internal(badger, key, amount):
    digg = badger.digg
    manager = badger.badgerRewardsManager
    console.log({"swap": key, "amount": amount})
    if key == "native.uniBadgerWbtc":
        # ===== native.uniBadgerWbtc =====
        manager.swapExactTokensForTokensUniswap(
            badger.token,
            amount,
            [badger.token, registry.tokens.wbtc],
            {"from": badger.keeper, "gas_limit": 1000000},
        )
        return True
    if key == "native.sushiBadgerWbtc":
        manager.swapExactTokensForTokensSushiswap(
            badger.token,
            amount,
            [badger.token, registry.tokens.wbtc],
            {"from": badger.keeper, "gas_limit": 1000000},
        )
        return True
    if key == "native.uniDiggWbtc":
        manager.swapExactTokensForTokensUniswap(
            digg.token,
            amount,
            [digg.token, registry.tokens.wbtc],
            {"from": badger.keeper, "gas_limit": 1000000},
        )
    if key == "native.sushiDiggWbtc":
        manager.swapExactTokensForTokensSushiswap(
            digg.token,
            amount,
            [digg.token, registry.tokens.wbtc],
            {"from": badger.keeper, "gas_limit": 1000000},
        )
        return True


def is_lp_sett(key):
    return "uni" in key or "sushi" in key


def is_uni_sett(key):
    return "uni" in key


def is_sushi_sett(key):
    return "sushi" in key


def main():
    """
    Swap daily allowance for LP tokens & run injection harvest
    """

    badger = connect_badger("deploy-finxal.json", load_keeper=True)
    rewards = get_active_rewards_schedule(badger)

    if rpc.is_active():
        """
        Test: Load up sending accounts with ETH and whale tokens
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    # swap one day of tokens

    manager = badger.badgerRewardsManager

    # # ===== native.uniBadgerWbtc =====
    key = "native.uniBadgerWbtc"
    swap_for_strategy(
        badger,
        key,
        rewards.getDistributions(key).getToStakingRewardsDaily("badger") // 2,
    )
    lp_for_strategy(badger, key)

    # ===== native.sushiBadgerWbtc =====
    key = "native.sushiBadgerWbtc"
    swap_for_strategy(
        badger,
        key,
        rewards.getDistributions(key).getToStakingRewardsDaily("badger") // 2,
    )
    lp_for_strategy(badger, key)

    # # ===== native.uniDiggWbtc =====
    key = "native.uniDiggWbtc"
    swap_for_strategy(
        badger,
        key,
        shares_to_fragments(
            rewards.getDistributions(key).getToStakingRewardsDaily("digg") // 2
        ),
    )
    lp_for_strategy(badger, key)

    # # ===== native.sushiDiggWbtc =====
    key = "native.sushiDiggWbtc"
    swap_for_strategy(
        badger,
        key,
        shares_to_fragments(
            rewards.getDistributions(key).getToStakingRewardsDaily("digg") // 2
        ),
    )
    lp_for_strategy(badger, key)

    rapid_harvest(badger)
