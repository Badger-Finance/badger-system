from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from tests.test_recorder import EventRecord, TestRecorder

@pytest.fixture(autouse=True)
def setup():
    # Assign accounts
    deployer = accounts[0]
    affiliate = accounts[1]
    manager = accounts[2]
    guardian = accounts[3]
    randomUser1 = accounts[4]
    randomUser2 = accounts[5]
    yearnGovernance = account[6]

    # WBTC (mainnet)
    # wbtc = registry.eth.eth_registry.token_registry.wbtc
    mockToken = deployer.deploy(MockToken)
    mockToken.initialize([randomUser1.address, randomUser2.address], [10000000000000000000, 10000000000000000000])

    # Yearn underlying vault
    vault = deployer.deploy(YearnTokenVault)
    mockToken.initialize(mockToken.contract_address, deployer.address, AddressZero, "YearnWBTC", "vyWBTC")

    # Yearn registry
    yearnRegistry = deployer.deploy(YearnRegistr)
    yearnRegistry.setGovernance(yearnGovernance)
    # Add vault to registry
    yearnRegistry.newRelease(vault.contract_address)

    # Deploy and initialize the wrapper contract (deployer -> affiliate)
    wrapper = deployer.deploy(AffiliateTokenGatedUpgradable)
    wrapper.initialize(mockToken.contract_address, yearnRegistry.contract_address, "BadgerYearnWBTC", "bvyWBTC", guardian.address)

    # Deploy the Guestlist contract (deployer -> bouncer)
    guestlist = deployer.deploy(VipCappedGuestList, wrapper.contract_address)

    # Add users to guestlist
    guestlist.setGuests([randomUser1.address, randomUser2.address], [True, False])

    yield


def test_permissions():