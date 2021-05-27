from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.gas_utils import gas_strategies
gas_strategies.set_default(gas_strategies.exponentialScalingFast)

to_add = "0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"
to_remove = "0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"

def main():
    badger = connect_badger()
    safe = ApeSafe(badger.devMultisig.address)
    badgerTree = safe.contract(badger.badgerTree.address)
    badgerTree.grantRole(ROOT_PROPOSER_ROLE, to_add)
    badgerTree.revokeRole(ROOT_PROPOSER_ROLE, to_remove)

    helper = ApeSafeHelper(badger, safe)
    helper.publish()