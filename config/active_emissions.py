from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp


""" 
Sett              Badger            GDigg
----------------  ------------      -------------
Badger UNI      : 6288.82 (half)       0
Badger Sushi    : 6288.82 (half)       0
Badger Native   : 3144.41 (half)       0
Sushi wbtcEth   : 4918.18              0
Crv RenBTC      : 4918.18              0
Crv SBTC        : 2459.09              0
Crv TBTC        : 2459.09              0
Harvest RenBTC  : 0.00                 0

Digg UNI        : 0                 14.949 (half)
Digg Sushi      : 0                 14.949 (half)
Digg Native     : 0                 7.475 (half)
Yearn WBTC      : 24590.90             0
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("6288.82 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("6288.82 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {
        "badger": Wei("3144.41 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("4918.18 ether"),
        "digg": to_digg_shares(0),
    },
    "native.renCrv": {
        "badger": Wei("4918.18 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sbtcCrv": {
        "badger": Wei("2459.09 ether"),
        "digg": to_digg_shares(0),
    },
    "native.tbtcCrv": {
        "badger": Wei("2459.09 ether"),
        "digg": to_digg_shares(0),
    },
    "harvest.renCrv": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(0),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(14.949),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(14.949),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(7.475)},
    "yearn.wbtc": {"badger": Wei("24590.90 ether"), "digg": to_digg_shares(0)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 5, 13, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
