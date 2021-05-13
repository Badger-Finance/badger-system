from helpers.utils import digg_shares_to_initial_fragments
from helpers.token_utils import print_balances, to_token, val
from brownie import *
from config.badger_config import badger_config
from helpers.time_utils import hours, to_days, to_utc_date, days
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.registry import registry


def main():
    badger = connect_badger()

    for key, sett in badger.sett_system.vaults.items():
        badger.print_logger_unlock_schedules(sett, name=key)
