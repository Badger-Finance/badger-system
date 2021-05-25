import datetime
from enum import Enum
from helpers.token_utils import distribute_from_whales
from helpers.proxy_utils import deploy_proxy
import json
import os
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
import warnings
import requests
import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.gnosis_safe import convert_to_test_mode, exec_direct, get_first_owner
from helpers.constants import MaxUint256
from scripts.systems.sushiswap_system import SushiswapSystem

console = Console()

strat_keys = [
    "native.badger",
    "native.uniBadgerWbtc",
    "native.sushiBadgerWbtc",
    "native.digg",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
]


def snap_strategy_balance(strategy, manager):
    want = interface.IERC20(strategy.want())

    state = {
        "manager": want.balanceOf(manager),
        "balanceOfPool": strategy.balanceOfPool(),
        "balanceOfWant": strategy.balanceOfWant(),
        "balanceOf": strategy.balanceOf(),
    }
    return state


def diff_numbers_by_key(a, b):
    diff = {}
    for key, a_value in a.items():
        b_value = b[key]
        diff[key] = b_value - a_value
    return diff


def main():
    test_main()


def test_main():
    badger = connect_badger("deploy-final.json")
    digg = connect_digg("deploy-final.json")

    distribute_from_whales(badger.keeper)

    manager = setup()
    deployer = badger.deployer
    keeper = badger.keeper

    badger.token.transfer(manager, Wei("1000 ether"), {"from": badger.keeper})
    digg.token.transfer(manager, Wei("100 gwei"), {"from": badger.keeper})

    before = badger.token.balanceOf(badger.devMultisig)
    wbtc = interface.IERC20(registry.tokens.wbtc)

    badger_swap_amount = Wei("100 ether")
    digg_swap_amount = Wei("10 gwei")
    badger_transfer_amount = Wei("10 ether")
    digg_transfer_amount = Wei("1 gwei")

    # with brownie.reverts("Initializable: contract is already initialized"):
    #     manager.initialize(
    #         badger.deployer,
    #         badger.keeper,
    #         badger.keeper,
    #         badger.guardian,
    #         badger.devMultisig,
    #         {"from": badger.keeper},
    #     ),

    testStrat = badger.getStrategy("native.badger")

    # # Can add strategy
    # manager.approveStrategy(testStrat, {"from": deployer})
    # assert manager.isApprovedStrategy(testStrat) == True

    # # Can revoke strategy
    # manager.revokeStrategy(testStrat, {"from": deployer})
    # assert manager.isApprovedStrategy(testStrat) == False

    # Get tokens
    before = wbtc.balanceOf(manager)
    manager.swapExactTokensForTokensUniswap(
        badger.token,
        badger_swap_amount,
        [badger.token, registry.tokens.wbtc],
        {"from": keeper},
    )
    after = wbtc.balanceOf(manager)

    console.print("token swap uni", {"before": before, "after": after})
    assert after > before

    manager.swapExactTokensForTokensSushiswap(
        badger.token,
        badger_swap_amount,
        [badger.token, registry.tokens.wbtc],
        {"from": keeper},
    )
    after2 = wbtc.balanceOf(manager)

    console.print(
        "token swap sushi", {"before": before, "after": after, "after2": after2}
    )

    assert after2 > after

    for key in strat_keys:
        console.print("[blue]=== Running for {} ===[/blue]".format(key))
        strat = badger.getStrategy(key)
        # manager.approveStrategy(strat, {"from": deployer})

        # ===== Convert And Transfer Assets
        want = interface.IERC20(strat.want())

        # Native Staking
        if key == "native.badger":
            before = snap_strategy_balance(strat, manager)
            manager.transferWant(
                strat.want(), strat, badger_transfer_amount, {"from": keeper}
            )
            after = snap_strategy_balance(strat, manager)
            diff = diff_numbers_by_key(before, after)

            console.log("transfer only", key, before, after, diff)

        if key == "native.digg":
            before = snap_strategy_balance(strat, manager)
            manager.transferWant(
                strat.want(), strat, digg_transfer_amount, {"from": keeper}
            )
            after = snap_strategy_balance(strat, manager)
            diff = diff_numbers_by_key(before, after)

            console.log("transfer only", key, before, after, diff)

        startToken = ""
        amount = 0
        if "Badger" in key:
            startToken = badger.token
            amount = badger_swap_amount
        elif "Digg" in key:
            startToken = digg.token
            amount = digg_swap_amount

        # LP Setts
        if "uni" in key:
            before = snap_strategy_balance(strat, manager)

            console.print(
                "PreSwap", {"key": key, "startToken": startToken, "amount": amount}
            )

            manager.swapExactTokensForTokensUniswap(
                startToken, amount, [startToken, wbtc], {"from": keeper}
            )

            manager.addLiquidityUniswap(startToken, wbtc, {"from": keeper})

            after_swap = snap_strategy_balance(strat, manager)
            diff_swap = diff_numbers_by_key(before, after_swap)

            console.log("post swap", key, before, after_swap, diff_swap)

            manager.transferWant(
                strat.want(), strat, want.balanceOf(manager), {"from": keeper}
            )
            after_transfer = snap_strategy_balance(strat, manager)
            diff_transfer = diff_numbers_by_key(after_swap, after_transfer)

            console.log("post transfer", key, after_swap, after_transfer, diff_transfer)

        if "sushi" in key:
            before = snap_strategy_balance(strat, manager)
            manager.swapExactTokensForTokensSushiswap(
                startToken, amount, [startToken, wbtc], {"from": keeper}
            )

            manager.addLiquiditySushiswap(startToken, wbtc, {"from": keeper})

            after_swap = snap_strategy_balance(strat, manager)
            diff_swap = diff_numbers_by_key(before, after_swap)

            console.log("post swap", key, before, after_swap, diff_swap)

            manager.transferWant(
                strat.want(), strat, want.balanceOf(manager), {"from": keeper}
            )
            after_transfer = snap_strategy_balance(strat, manager)
            diff_transfer = diff_numbers_by_key(after_swap, after_transfer)

            console.log("post transfer", key, after_swap, after_transfer, diff_transfer)

        tx = manager.deposit(strat, {"from": keeper})
        print("deposit events", tx.events)
        if strat.isTendable():
            tx = manager.tend(strat, {"from": keeper})
            print("tend events", tx.events)
        if key != "native.uniBadgerWbtc":
            tx = manager.harvest(strat, {"from": keeper})
            print("harvest events", tx.events)

    # Tend

    # Harvest


def setup():
    """
    Connect to badger system, and configure multisig for running transactions in local fork without access to accounts
    """

    # Connect badger system from file
    badger = connect_badger("deploy-final.json")
    digg = connect_digg("deploy-final.json")

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    # Multisig wrapper
    multi = GnosisSafe(badger.devMultisig, testMode=True)
    manager = BadgerRewardsManager.at("0x5B60952481Eb42B66bdfFC3E049025AC5b91c127")

    for key in strat_keys:
        print(key)
        strategy = badger.getStrategy(key)
        multi.execute(
            MultisigTxMetadata(description="Transfer Keeper for {}".format(key)),
            {"to": strategy.address, "data": strategy.setKeeper.encode_input(manager)},
        )

    return manager
