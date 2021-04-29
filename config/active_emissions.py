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
Badger UNI      : 7460.87 (half)       0
Badger Sushi    : 7460.87 (half)       0
Badger Native   : 3730.43 (half)        0
Sushi wbtcEth   : 5834.78              0
Crv RenBTC      : 5834.78              0
Crv SBTC        : 5834.78              0
Crv TBTC        : 5834.78              0
Harvest RenBTC  : 5834.78              0

Digg UNI        : 0                 17.735 (half)
Digg Sushi      : 0                 17.735 (half)
Digg Native     : 0                 8.868 (half)
Yearn WBTC      : 23339.12             0
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("7460.87 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("7460.87 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {
        "badger": Wei("3730.43 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("5834.78 ether"),
        "digg": to_digg_shares(0),
    },
    "native.renCrv": {
        "badger": Wei("5834.78 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sbtcCrv": {
        "badger": Wei("5834.78 ether"),
        "digg": to_digg_shares(0),
    },
    "native.tbtcCrv": {
        "badger": Wei("5834.78 ether"),
        "digg": to_digg_shares(0),
    },
    "harvest.renCrv": {
        "badger": Wei("5834.78 ether"),
        "digg": to_digg_shares(0),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(17.735),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(17.735),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(8.868)},
    "yearn.wbtc": {"badger": Wei("23339.12 ether"), "digg": to_digg_shares(0)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 4, 29, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
