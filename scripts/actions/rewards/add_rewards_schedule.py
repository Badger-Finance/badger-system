from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from config.active_emissions import emissions, get_active_rewards_schedule
import datetime
import json
import os
from scripts.actions.helpers.GeyserDistributor import GeyserDistributor
from scripts.actions.helpers.StakingRewardsDistributor import StakingRewardsDistributor
import time
import warnings

import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()


def main():
    badger = connect_badger()
    admin = badger.devProxyAdmin
    multisig = badger.devMultisig
    contracts = badger.contracts_upgradeable
    deployer = badger.deployer

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert multisig == expectedMultisig

    rest = get_active_rewards_schedule(badger)

    rest.printState("Week ?? - who knows anymore")

    recipient = accounts.at(expectedMultisig, force=True)

    # rest.transfer(badger.token, 33038371371007690000000, recipient)
    # rest.transfer(badger.digg.token, Wei("3 gwei"), badger.treasuryMultisig)

    rest.testTransactions()
    console.print(rest.totals)
    console.print(shares_to_fragments(rest.totals["digg"]))

    # print("overall total ", total)
    # print("expected total ", expected)

    # assert total == expected

    # console.print(
    #     "\n[green] ✅ Total matches expected {} [/green]".format(val(expected))
    # )
