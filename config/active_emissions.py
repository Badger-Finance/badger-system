from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp


""" 
Sett              Badger            Digg
----------------  ------------      -------------
Badger UNI      : 19034.72 (half)       8.347
Badger Sushi    : 19034.72 (half)       8.347
Badger Native   : 9517.36 (half)        3.77
Sushi wbtcEth   : 14886.13              6.528
Crv RenBTC      : 14886.13              6.528
Crv SBTC        : 14886.13              6.528
Crv TBTC        : 14886.13              6.528
Harvest RenBTC  : 14886.13              6.528

Digg UNI        : 0                 23.844 (half)
Digg Sushi      : 0                 23.844 (half)
Digg Native     : 0                 11.922 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("19034.72 ether"),
        "digg": to_digg_shares(8.347),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("19034.72 ether"),
        "digg": to_digg_shares(8.347),
    },
    "native.badger": {
        "badger": Wei("9517.36 ether"),
        "digg": to_digg_shares(3.77),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("14886.13 ether"),
        "digg": to_digg_shares(6.528),
    },
    "native.renCrv": {
        "badger": Wei("14886.13 ether"),
        "digg": to_digg_shares(6.528),
    },
    "native.sbtcCrv": {
        "badger": Wei("14886.13 ether"),
        "digg": to_digg_shares(6.528),
    },
    "native.tbtcCrv": {
        "badger": Wei("14886.13 ether"),
        "digg": to_digg_shares(6.528),
    },
    "harvest.renCrv": {
        "badger": Wei("14886.13 ether"),
        "digg": to_digg_shares(6.528),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(23.844),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(23.844),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(11.922)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 2, 18, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
