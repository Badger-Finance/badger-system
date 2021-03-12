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
Badger UNI      : 14166.61 (half)       3.002
Badger Sushi    : 14166.61 (half)       3.002
Badger Native   : 7083.30 (half)        1.501
Sushi wbtcEth   : 11079.11              2.348
Crv RenBTC      : 11079.11              2.348
Crv SBTC        : 11079.11              2.348
Crv TBTC        : 11079.11              2.348
Harvest RenBTC  : 11079.11              2.348

Digg UNI        : 0                 25.978 (half)
Digg Sushi      : 0                 25.978 (half)
Digg Native     : 0                 12.989 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("14166.61 ether"),
        "digg": to_digg_shares(3.002),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("14166.61 ether"),
        "digg": to_digg_shares(3.002),
    },
    "native.badger": {
        "badger": Wei("7083.30 ether"),
        "digg": to_digg_shares(1.501),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("11079.11 ether"),
        "digg": to_digg_shares(2.348),
    },
    "native.renCrv": {
        "badger": Wei("11079.11 ether"),
        "digg": to_digg_shares(2.348),
    },
    "native.sbtcCrv": {
        "badger": Wei("11079.11 ether"),
        "digg": to_digg_shares(2.348),
    },
    "native.tbtcCrv": {
        "badger": Wei("11079.11 ether"),
        "digg": to_digg_shares(2.348),
    },
    "harvest.renCrv": {
        "badger": Wei("11079.11 ether"),
        "digg": to_digg_shares(2.348),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(25.978),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(25.978),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(12.989)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 3, 11, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
