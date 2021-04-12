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
Badger UNI      : 11714.61 (half)       1.990
Badger Sushi    : 11714.61 (half)       1.990
Badger Native   : 5857.30 (half)        0.995
Sushi wbtcEth   : 9161.42              1.556
Crv RenBTC      : 9161.42              1.556
Crv SBTC        : 9161.42              1.556
Crv TBTC        : 9161.42              1.556
Harvest RenBTC  : 9161.42              1.556

Digg UNI        : 0                 22.744 (half)
Digg Sushi      : 0                 22.744 (half)
Digg Native     : 0                 11.372 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("11714.61 ether"),
        "digg": to_digg_shares(1.990),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("11714.61 ether"),
        "digg": to_digg_shares(1.990),
    },
    "native.badger": {
        "badger": Wei("5857.30 ether"),
        "digg": to_digg_shares(0.995),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("9161.42 ether"),
        "digg": to_digg_shares(1.556),
    },
    "native.renCrv": {
        "badger": Wei("9161.42 ether"),
        "digg": to_digg_shares(1.556),
    },
    "native.sbtcCrv": {
        "badger": Wei("9161.42 ether"),
        "digg": to_digg_shares(1.556),
    },
    "native.tbtcCrv": {
        "badger": Wei("9161.42 ether"),
        "digg": to_digg_shares(1.556),
    },
    "harvest.renCrv": {
        "badger": Wei("9161.42 ether"),
        "digg": to_digg_shares(1.556),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(22.744),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(22.744),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(11.372)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 3, 25, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
