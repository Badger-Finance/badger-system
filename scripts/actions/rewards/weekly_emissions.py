from helpers.rewards.LoggerUnlockSchedule import LoggerUnlockSchedule
from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from config.active_emissions import (
    build_weekly_schedules,
    emissions,
    get_active_rewards_schedule,
)
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

start = to_timestamp(datetime.datetime(2021, 7, 8, 13, 00))
duration = days(7)


def set_schedules(logger, schedules):
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


def main():
    badger = connect_badger(load_deployer=True)

    safe = ApeSafe(badger.opsMultisig.address)
    helper = ApeSafeHelper(badger, safe)
    logger = helper.contract_from_abi(
        badger.rewardsLogger.address, "RewardsLogger", RewardsLogger.abi
    )

    schedules = build_weekly_schedules(badger, start, duration)
    console.print(schedules)
    set_schedules(logger, schedules)

    for key in badger.getAllSettIds():
        sett = badger.getSett(key)
        badger.print_logger_unlock_schedules(sett.address, name=sett.name())

    helper.publish()
