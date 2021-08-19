from scripts.view.acl_viewer import print_access_control
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from ape_safe import ApeSafe
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger

accounts = ["0x86cbD0ce0c087b482782c181dA8d191De18C8275"]

def main():
    badger = connect_badger()
    safe = ApeSafe(badger.opsMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    contract = helper.contract_from_abi(badger.rewardsLogger.address, "IAccessControl", interface.IAccessControl.abi)
    print_access_control(contract)

    for account in accounts:
        contract.grantRole(MANAGER_ROLE, account)

    helper.publish()
