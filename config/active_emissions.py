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
Badger UNI      : 17226.42 (half)       6.990
Badger Sushi    : 17226.42 (half)       6.990
Badger Native   : 8613.21 (half)        3.495
Sushi wbtcEth   : 13471.95              5.467
Crv RenBTC      : 13471.95              5.467
Crv SBTC        : 13471.95              5.467
Crv TBTC        : 13471.95              5.467
Harvest RenBTC  : 13471.95              5.467

Digg UNI        : 0                 23.025 (half)
Digg Sushi      : 0                 23.025 (half)
Digg Native     : 0                 11.513 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("17226.42 ether"),
        "digg": to_digg_shares(6.990),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("17226.42 ether"),
        "digg": to_digg_shares(6.990),
    },
    "native.badger": {
        "badger": Wei("8613.21 ether"),
        "digg": to_digg_shares(3.495),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("13471.95 ether"),
        "digg": to_digg_shares(5.467),
    },
    "native.renCrv": {
        "badger": Wei("13471.95 ether"),
        "digg": to_digg_shares(5.467),
    },
    "native.sbtcCrv": {
        "badger": Wei("13471.95 ether"),
        "digg": to_digg_shares(5.467),
    },
    "native.tbtcCrv": {
        "badger": Wei("13471.95 ether"),
        "digg": to_digg_shares(5.467),
    },
    "harvest.renCrv": {
        "badger": Wei("13471.95 ether"),
        "digg": to_digg_shares(5.467),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(23.025),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(23.025),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(11.513)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 2, 25, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
