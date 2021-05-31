from helpers.rewards.LoggerUnlockSchedule import LoggerUnlockSchedule
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
    ApeSafeHelper,
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
from ape_safe import ApeSafe

console = Console()
pretty.install()


def main():
    badger = connect_badger(load_deployer=True)
    admin = badger.devProxyAdmin
    multisig = badger.devMultisig
    contracts = badger.contracts_upgradeable
    deployer = badger.deployer

    safe = ApeSafe(badger.opsMultisig.address)
    logger = safe.contract(badger.rewardsLogger.address)

    experimental_vault = "0x8a8ffec8f4a0c8c9585da95d9d97e8cd6de273de"

    start = 1620943200
    duration = days(7)
    end = start + duration

    badger_amount = int(Wei("4000 ether") * 0.9)
    digg_amount = int(fragments_to_shares(0.4) * 0.9)
    dfd_amount = int(Wei("205131 ether") * 0.9)

    schedules = [
        LoggerUnlockSchedule(
            (
                experimental_vault,
                badger.token.address,
                badger_amount,
                start,
                end,
                duration,
            )
        ),
        LoggerUnlockSchedule(
            (
                experimental_vault,
                badger.digg.token.address,
                digg_amount,
                start,
                end,
                duration,
            )
        ),
        LoggerUnlockSchedule(
            (experimental_vault, registry.tokens.dfd, dfd_amount, start, end, duration)
        ),
    ]

    for i in range(0, len(schedules)):
        schedule = schedules[i]
        logger.setUnlockSchedule(
            schedule.beneficiary,
            schedule.token,
            schedule.amount,
            schedule.start,
            schedule.end,
            schedule.duration,
        )

    badger.print_logger_unlock_schedules(
        experimental_vault, name="Experimental iBBTC Vault"
    )

    helper = ApeSafeHelper(badger, safe)
    helper.publish()
