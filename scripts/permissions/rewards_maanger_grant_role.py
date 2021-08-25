from scripts.permissions.access_control import BadgerRewardsManagerHelper
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger

def main():
    badger = connect_badger()
    safe = ApeSafe(badger.devMultisig.address)
    helper = ApeSafeHelper(badger, safe)
    
    rm = BadgerRewardsManagerHelper(badger, helper)
    rm.grant_role_on_rewards_manager(KEEPER_ROLE, ["0xF8dbb94608E72A3C4cEeAB4ad495ac51210a341e"])

    helper.publish()
