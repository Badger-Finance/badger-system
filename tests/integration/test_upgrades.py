from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config


def test_confirm_contract_admins(badger):
    owner = badger.deployer

    assert badger.devProxyAdmin.owner() == owner

    # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
    for contract in badger.contracts:
        assert (
            badger.devProxyAdmin.getProxyImplementation(contract)
            == badger.logic.BadgerTree
        )
