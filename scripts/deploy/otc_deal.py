from helpers.token_utils import distribute_from_whales, distribute_test_ether, get_token_balances, print_balances
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

    test_user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    distribute_test_ether(test_user, Wei("20 ether"))
    distribute_from_whales(test_user, assets=["bBadger", "usdc"])

    rest = get_active_rewards_schedule(badger)
    usdc = interface.IERC20(registry.tokens.usdc)

    params = {
        "beneficiary": test_user,
        "cliffDuration": days(365),
        "duration": days(365),
        "usdcAmount": 1000 * 10 ** 6,
        "bBadgerAmount": Wei("10 ether"),
    }

    escrow = OtcEscrow.deploy(
        params["beneficiary"],
        params["duration"],
        params["usdcAmount"],
        params["bBadgerAmount"],
        {"from": badger.deployer},
    )

    bBadger = badger.getSett("native.badger")
    bBadger.transfer(escrow, params["bBadgerAmount"], {'from': test_user})

    pre = get_token_balances([usdc, bBadger], [test_user, escrow, badger.devMultisig])
    console.print(pre)

    usdc.approve(escrow, params["usdcAmount"], {'from': test_user})
    tx = escrow.swap({'from': test_user})
    post = get_token_balances([usdc, bBadger], [test_user, escrow, badger.devMultisig])

    console.print(tx.events)
    console.print(post)

    vesting = TokenTimelock.at(tx.events["VestingDeployed"][0]['vesting'])
    
    console.print({
        'token': vesting.token(),
        'beneficiary': vesting.beneficiary(),
        'releaseTime': to_utc_date(vesting.releaseTime())
    })

    chain.sleep(days(365))
    chain.mine()

    vesting.release({'from': test_user})