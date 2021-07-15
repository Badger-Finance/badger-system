from helpers.utils import digg_shares_to_initial_fragments
from helpers.token_utils import print_balances, to_token, val
from brownie import *
from config.badger_config import badger_config
from helpers.time_utils import hours, to_days, to_utc_date, days
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.registry import registry


class UnlockSchedule:
    def __init__(self, token, raw_schedule):
        self.token = token
        self.amount = raw_schedule[0]
        self.end = raw_schedule[1]
        self.duration = raw_schedule[2]
        self.start = raw_schedule[3]


skip = [
    # "native.badger",
    # "native.renCrv",
    # "native.sbtcCrv",
    # "native.tbtcCrv",
    # "native.uniBadgerWbtc",
    # "harvest.renCrv",
    # "native.sushiWbtcEth",
    # "native.sushiBadgerWbtc",
    # "native.digg",
    # "native.uniDiggWbtc",
    # "native.sushiDiggWbtc",
    # "yearn.wbtc",
    # "experimental.sushiIBbtcWbtc"
]


def main():
    badger = connect_badger()
    table = []

    for key, geyser in badger.geysers.items():
        if key in skip:
            continue
        badger.print_latest_unlock_schedules(geyser, name=key)
