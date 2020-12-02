from brownie import *
from dotmap import DotMap
import pytest
from helpers.constants import *

@pytest.mark.skip()
def test_re_initializations(badger_prod):
    """
    Ensure that every contract in the system is initialized
    Ensure any attempts to re-initialize will revert
    """

    # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
    for contract in badger_prod.contracts_upgradeable:
        assert contract.initialized() == True
