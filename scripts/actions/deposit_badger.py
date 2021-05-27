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
    to_digg_shares,
    tx_wait,
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

    multi = GnosisSafe(badger.opsMultisig)

    account = accounts.load("badger_proxy_deployer")
    print(account.address)

    amount = Wei("10000 ether")

    # print(badger.deployer)
    # print(badger.token.balanceOf(badger.deployer), badger.token.balanceOf(badger.opsMultisig))

    # multi.execute(MultisigTxMetadata(description="Transfer badger to EOA"), {
    #     "to": badger.token.address,
    #     "data": badger.token.transfer.encode_input(account, Wei("10000 ether"))
    # })

    # print(badger.token.balanceOf(account), badger.token.balanceOf(badger.opsMultisig))

    # assert badger.token.balanceOf(account) >= amount

    bBadger = badger.getSett("native.badger")
    # badger.token.approve(bBadger, amount, {"from": account})

    # bBadger.deposit(amount, {"from": account})
    # tx_wait()
    print(bBadger.balanceOf(account))

    airdropProxy = AirdropDistributor.at("0xd17c7effa924b55951e0f6d555b3a3ea34451179")
    bBadger.transfer(airdropProxy, bBadger.balanceOf(account), {"from": account})

    # rest = get_active_rewards_schedule(badger)

    # rest.printState("Week ?? - who knows anymore")

    # rest.transfer(badger.token, Wei("11000 ether"), badger.opsMultisig)
    # rest.testTransactions()

    # print("overall total ", total)
    # print("expected total ", expected)

    # assert total == expected
