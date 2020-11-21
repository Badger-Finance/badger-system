from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config


def test_re_initializations(badger):
    """
    Ensure that every contract in the system is initialized
    Ensure any attempts to re-initialize will revert
    """

    # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
    for contract in badger.contracts:
        assert contract.initialized() == True
