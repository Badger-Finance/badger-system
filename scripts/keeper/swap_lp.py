from scripts.keeper.rapid_harvest import rapid_harvest
from helpers.snapshot import diff_numbers_by_key, snap_strategy_balance
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem

from helpers.utils import shares_to_fragments, to_digg_shares, to_tabulate, tx_wait
from helpers.sett.SnapshotManager import SnapshotManager
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from assistant.rewards.rewards_checker import val
from config.active_emissions import active_emissions, get_daily_amount, get_half_daily_amount

gas_strategy = GasNowStrategy("fast")

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

    console.print("[green]==Swap for {}==[/green]".format(key))
    to_tabulate("Diff {}".format(key), diff)


def lp_for_strategy_internal(badger, key):
    digg = badger.digg
    manager = badger.badgerRewardsManager
    if key == "native.uniBadgerWbtc":
        manager.addLiquidityUniswap(badger.token, wbtc, {"from": badger.keeper})
    if key == "native.sushiBadgerWbtc":
        manager.addLiquiditySushiswap(badger.token, wbtc, {"from": badger.keeper})
    if key == "native.uniDiggWbtc":
        manager.addLiquidityUniswap(digg.token, wbtc, {"from": badger.keeper})
    if key == "native.sushiDiggWbtc":
        manager.addLiquiditySushiswap(digg.token, wbtc, {"from": badger.keeper})


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
    if key == "native.uniBadgerWbtc":
        # ===== native.uniBadgerWbtc =====
        manager.swapExactTokensForTokensUniswap(
            badger.token,
            amount,
            [badger.token, registry.tokens.wbtc],
            {"from": badger.keeper},
        )
        return True
    if key == "native.sushiBadgerWbtc":
        manager.swapExactTokensForTokensSushiswap(
            badger.token,
            amount,
            [badger.token, registry.tokens.wbtc],
            {"from": badger.keeper},
        )
        return True
    if key == "native.uniDiggWbtc":
        manager.swapExactTokensForTokensUniswap(
            digg.token,
            amount,
            [digg.token, registry.tokens.wbtc],
            {"from": badger.keeper},
        )
    if key == "native.sushiDiggWbtc":
        manager.swapExactTokensForTokensSushiswap(
            digg.token,
            amount,
            [digg.token, registry.tokens.wbtc],
            {"from": badger.keeper},
        )
        return True


def is_lp_sett(key):
    if "uni" in key:
        return True
    if "sushi" in key:
        return True
    else:
        return False


def is_uni_sett(key):
    if "uni" in key:
        return True
    else:
        return False


def is_sushi_sett(key):
    if "sushi" in key:
        return True
    else:
        return False


def main():
    """
    Swap daily allowance for LP tokens & run injection harvest
    """

    badger = connect_badger("deploy-final.json", load_keeper=True)
    digg = badger.digg

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
    swap_for_strategy(badger, key, get_half_daily_amount(key, "badger"))
    lp_for_strategy(badger, key)

    # ===== native.sushiBadgerWbtc =====
    key = "native.sushiBadgerWbtc"
    swap_for_strategy(badger, key, get_daily_amount(key, "badger"))
    lp_for_strategy(badger, key)

    # # ===== native.uniDiggWbtc =====
    key = "native.uniDiggWbtc"
    swap_for_strategy(badger, key, get_half_daily_amount(key, "digg"))
    lp_for_strategy(badger, key)

    # # ===== native.sushiDiggWbtc =====
    key = "native.sushiDiggWbtc"
    swap_for_strategy(badger, key, get_half_daily_amount(key, "digg"))
    lp_for_strategy(badger, key)

    rapid_harvest()
