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
Badger UNI      : 8143.27 (half)       0
Badger Sushi    : 8143.27 (half)       0
Badger Native   : 4071.64 (half)        0
Sushi wbtcEth   : 6368.46              0
Crv RenBTC      : 6368.46              0
Crv SBTC        : 6368.46              0
Crv TBTC        : 6368.46              0
Harvest RenBTC  : 6368.46              0

Digg UNI        : 0                 19.357 (half)
Digg Sushi      : 0                 19.357 (half)
Digg Native     : 0                 9.679 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("8143.27 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("8143.27 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {"badger": Wei("4071.64 ether"), "digg": to_digg_shares(0),},
    "native.sushiWbtcEth": {"badger": Wei("6368.46 ether"), "digg": to_digg_shares(0),},
    "native.renCrv": {"badger": Wei("6368.46 ether"), "digg": to_digg_shares(0),},
    "native.sbtcCrv": {"badger": Wei("6368.46 ether"), "digg": to_digg_shares(0),},
    "native.tbtcCrv": {"badger": Wei("6368.46 ether"), "digg": to_digg_shares(0),},
    "harvest.renCrv": {"badger": Wei("6368.46 ether"), "digg": to_digg_shares(0),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(19.357),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(19.357),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(9.679)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 4, 22, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
