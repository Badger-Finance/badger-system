import datetime
import json
import os
import warnings
from enum import Enum

import brownie
import pytest
import requests
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gas_utils import gas_strategies
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.digg_system import connect_digg
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from tabulate import tabulate

console = Console()

gas_strategies.set_default_for_active_chain()


def rebase(badger: BadgerSystem, account):
    digg = badger.digg
    supplyBefore = digg.token.totalSupply()

    print("spfBefore", digg.token._sharesPerFragment())
    print("supplyBefore", digg.token.totalSupply())

    print(digg.cpiMedianOracle.getData.call())

    sushi = SushiswapSystem()
    pair = sushi.getPair(digg.token, registry.tokens.wbtc)

    uni = UniswapSystem()
    uniPair = uni.getPair(digg.token, registry.tokens.wbtc)

    last_rebase_time = digg.uFragmentsPolicy.lastRebaseTimestampSec()
    in_rebase_window = digg.uFragmentsPolicy.inRebaseWindow()
    now = chain.time()

    time_since_last_rebase = now - last_rebase_time

    console.print(
        {
            "last_rebase_time": last_rebase_time,
            "in_rebase_window": in_rebase_window,
            "now": now,
            "time_since_last_rebase": time_since_last_rebase,
        }
    )

    # Rebase if sufficient time has passed since last rebase and we are in the window.
    # Give adequate time between TX attempts
    if time_since_last_rebase > hours(2) and in_rebase_window:
        console.print("[bold yellow]===== 📈 Rebase! 📉=====[/bold yellow]")
        print("pair before", pair.getReserves())
        print("uniPair before", uniPair.getReserves())

        tx = digg.orchestrator.rebase({"from": account})

        if rpc.is_active():
            chain.mine()
            print(tx.call_trace())
            print(tx.events)

        supplyAfter = digg.token.totalSupply()

        print("spfAfter", digg.token._sharesPerFragment())
        print("supplyAfter", supplyAfter)
        print("supplyChange", supplyAfter / supplyBefore)
        print("supplyChangeOtherWay", supplyBefore / supplyAfter)

        print("pair after", pair.getReserves())
        print("uniPair after", uniPair.getReserves())
    else:
        console.print("[white]===== No Rebase =====[/white]")


def main():
    console.print("[white]===== Checking Parameters for rebase =====[/white]")
    # Connect badger system from file
    badger = connect_badger(load_deployer=True)
    rebase(badger, badger.deployer)
