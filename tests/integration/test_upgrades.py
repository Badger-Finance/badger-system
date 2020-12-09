from brownie import *
from helpers.constants import *


def test_confirm_contract_admins(badger):
    # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
    for key, contract in badger.contracts_upgradeable.items():
        print("testing upgradeability", key, contract)
        assert badger.devProxyAdmin.getProxyImplementation(contract) != AddressZero
