from helpers.utils import digg_shares_to_initial_fragments
from helpers.token_utils import print_balances, to_token, val
from brownie import *
from config.badger_config import badger_config
from helpers.time_utils import hours, to_days, to_utc_date, days
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.registry import registry

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

    for key, sett in badger.sett_system.vaults.items():
        if key in skip:
            continue
        badger.print_logger_unlock_schedules(sett, name=key)
