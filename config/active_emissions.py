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
Badger UNI      : 21063.10 (half)   7.54
Badger Sushi    : 21063.10 (half)   7.54
Badger Native   : 10531.55 (half)   3.77
Sushi wbtcEth   : 16472.42          5.897
Crv RenBTC      : 16472.42          5.897
Crv SBTC        : 16472.42          5.897
Crv TBTC        : 16472.42          5.897
Harvest RenBTC  : 16472.42          5.897

Digg UNI        : 0                 30.735 (half)
Digg Sushi      : 0                 30.735 (half)
Digg Native     : 0                 15.368 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("21063.10 ether"),
        "digg": to_digg_shares(7.54),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("21063.10 ether"),
        "digg": to_digg_shares(7.54),
    },
    "native.badger": {"badger": Wei("10531.55 ether"), "digg": to_digg_shares(3.77),},
    "native.sushiWbtcEth": {
        "badger": Wei("16472.42 ether"),
        "digg": to_digg_shares(5.897),
    },
    "native.renCrv": {"badger": Wei("16472.42 ether"), "digg": to_digg_shares(5.897),},
    "native.sbtcCrv": {"badger": Wei("16472.42 ether"), "digg": to_digg_shares(5.897),},
    "native.tbtcCrv": {"badger": Wei("16472.42 ether"), "digg": to_digg_shares(5.897),},
    "harvest.renCrv": {"badger": Wei("16472.42 ether"), "digg": to_digg_shares(5.897),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(30.735),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(30.735),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(15.368)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 2, 11, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    return rest
