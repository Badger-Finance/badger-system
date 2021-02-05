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
Badger UNI      : 23338.61 (half)   6.42
Badger Sushi    : 23338.61 (half)   6.42
Badger Native   : 11669.31 (half)   3.21
Sushi wbtcEth   : 18251.99          5.02
Crv RenBTC      : 18251.99          5.02
Crv SBTC        : 18251.99          5.02
Crv TBTC        : 18251.99          5.02
Harvest RenBTC  : 18251.99          5.02

Digg UNI        : 0                 39.00 (half)
Digg Sushi      : 0                 39.00 (half)
Digg Native     : 0                 19.50 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("23338.61 ether"),
        "digg": to_digg_shares(6.42),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("23338.61 ether"),
        "digg": to_digg_shares(6.42),
    },
    "native.badger": {"badger": Wei("11669.31 ether"), "digg": to_digg_shares(3.21),},
    "native.sushiWbtcEth": {
        "badger": Wei("18251.99 ether"),
        "digg": to_digg_shares(5.02),
    },
    "native.renCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.sbtcCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.tbtcCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "harvest.renCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(39.00),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(39.00),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(19.50)},
}

class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions

emissions = Emissions(active_emissions=weekly_schedule)

def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 2, 4, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    return rest
