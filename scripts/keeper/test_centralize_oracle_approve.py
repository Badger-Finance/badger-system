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
from helpers.tx_timer import tx_timer

console = Console()

gas_strategies.set_default_for_active_chain()


def approveReport(badger: BadgerSystem, account):
    digg = badger.digg
    oracle = CentralizedOracle.at("0x73083058e0f61D3fc7814eEEDc39F9608B4546d7")

    payload = oracle.proposedPayload()

    assert payload / 1e18 > 0.75
    assert payload / 1e18 < 1.25

    oracle.approveReport(payload, {'from': account})

    chain.mine()
    chain.sleep(hours(2))
    chain.mine()

    supplyBefore = digg.token.totalSupply()
    digg.orchestrator.rebase({'from': account})
    supplyAfter = digg.token.totalSupply()

    print({
        'supplyBefore': supplyBefore,
        'supplyAfter': supplyAfter,
        '%': supplyBefore / supplyAfter,
    })

def main():
    console.print("[white]===== Approving Report =====[/white]")
    # Connect badger system from file
    badger = connect_badger(load_rebaser=True)
    approveReport(badger, badger.rebaser)

    
