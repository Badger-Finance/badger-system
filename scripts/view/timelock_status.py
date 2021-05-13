from helpers.token_utils import (
    diff_token_balances,
    distribute_from_whales,
    distribute_test_ether,
    get_token_balances,
    print_balances,
)
from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from config.active_emissions import emissions, get_active_rewards_schedule
import datetime
import json
import os
from scripts.actions.helpers.GeyserDistributor import GeyserDistributor
from scripts.actions.helpers.StakingRewardsDistributor import StakingRewardsDistributor
import time
import warnings
import decouple
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
    badger = connect_badger("deploy-final.json")
    bBadger = badger.getSett("native.badger")

    escrows = [
        "0x1fc3C85456322C8514c0ff7694Ea4Ef5bC7F9f37",
        "0xaeDb773C226e6d74f2cd3542372076779Ff6fA6E",
    ]

    timelocks = [
        "0x2Bc1A5E26ad0316375E68942fe0B387adE6b9254",
        "0x7C651D13DfB87748b0F05914dFb40E5B15a78D35",
        "0xB6c9e9Ba41291044Cf5dadFB22D72d3fe9312880",
        "0xdbd185c59f64d2d39c6ababf5d701669417a002d"
        # "0x1fc3C85456322C8514c0ff7694Ea4Ef5bC7F9f37",
        # "0xaeDb773C226e6d74f2cd3542372076779Ff6fA6E"
    ]

    for address in timelocks:
        vesting = interface.ITokenTimelock(address)

        console.print(
            {
                "token": vesting.token(),
                "beneficiary": vesting.beneficiary(),
                "releaseTime": vesting.releaseTime(),
                "releaseDate": to_utc_date(vesting.releaseTime()),
            }
        )

    chain.sleep(days(182))
    chain.mine()

    for address in timelocks:
        vesting = interface.ITokenTimelock(address)
        beneficiary = accounts.at(vesting.beneficiary(), force=True)
        pre = get_token_balances([bBadger], [vesting, beneficiary])
        vesting.release({"from": badger.deployer})
        post = get_token_balances([bBadger], [vesting, beneficiary])
        diff_token_balances(pre, post)
