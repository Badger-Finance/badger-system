from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, fragments_to_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp

""" 
Sett              Badger            Digg
----------------  ------------      -------------
Badger UNI      : 21063.10 (half)   12.84
Badger Sushi    : 21063.10 (half)   12.84
Badger Native   : 10531.55 (half)   6.42
Sushi wbtcEth   : 16472.42          10.04
Crv RenBTC      : 16472.42          10.04
Crv SBTC        : 16472.42          10.04
Crv TBTC        : 16472.42          10.04
Harvest RenBTC  : 16472.42          10.04

Digg UNI        : 0                 52.35 (half)
Digg Sushi      : 0                 52.35 (half)
Digg Native     : 0                 26.17 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("21063.10 ether"),
        "digg": fragments_to_shares(12.84),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("21063.10 ether"),
        "digg": fragments_to_shares(12.84),
    },
    "native.badger": {"badger": Wei("10531.55 ether"), "digg": fragments_to_shares(6.42),},
    "native.sushiWbtcEth": {
        "badger": Wei("16472.42 ether"),
        "digg": fragments_to_shares(10.04),
    },
    "native.renCrv": {"badger": Wei("16472.42 ether"), "digg": fragments_to_shares(10.04),},
    "native.sbtcCrv": {"badger": Wei("16472.42 ether"), "digg": fragments_to_shares(10.04),},
    "native.tbtcCrv": {"badger": Wei("16472.42 ether"), "digg": fragments_to_shares(10.04),},
    "harvest.renCrv": {"badger": Wei("16472.42 ether"), "digg": fragments_to_shares(10.04),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": fragments_to_shares(52.35),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": fragments_to_shares(52.35),},
    "native.digg": {"badger": Wei("0 ether"), "digg": fragments_to_shares(26.17)},
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
