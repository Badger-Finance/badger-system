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
Badger UNI      : 12873.19 (half)       1.877
Badger Sushi    : 12873.19 (half)       1.877
Badger Native   : 6436.60 (half)        0.939
Sushi wbtcEth   : 10067.50              1.468
Crv RenBTC      : 10067.50              1.468
Crv SBTC        : 10067.50              1.468
Crv TBTC        : 10067.50              1.468
Harvest RenBTC  : 10067.50              1.468

Digg UNI        : 0                 25.787 (half)
Digg Sushi      : 0                 25.787 (half)
Digg Native     : 0                 12.894 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("12873.19 ether"),
        "digg": to_digg_shares(1.877),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("12873.19 ether"),
        "digg": to_digg_shares(1.877),
    },
    "native.badger": {
        "badger": Wei("6436.60 ether"),
        "digg": to_digg_shares(0.939),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("10067.50 ether"),
        "digg": to_digg_shares(1.468),
    },
    "native.renCrv": {
        "badger": Wei("10067.50 ether"),
        "digg": to_digg_shares(1.468),
    },
    "native.sbtcCrv": {
        "badger": Wei("10067.50 ether"),
        "digg": to_digg_shares(1.468),
    },
    "native.tbtcCrv": {
        "badger": Wei("10067.50 ether"),
        "digg": to_digg_shares(1.468),
    },
    "harvest.renCrv": {
        "badger": Wei("10067.50 ether"),
        "digg": to_digg_shares(1.468),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(25.787),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(25.787),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(12.894)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 3, 18, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
