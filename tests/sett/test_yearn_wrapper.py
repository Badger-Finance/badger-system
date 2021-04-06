from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from tests.test_recorder import EventRecord, TestRecorder
from tests.conftest import yearnSettTestConfig, badger_single_sett
from collections import namedtuple

@pytest.fixture(scope="module", autouse=True)
def setup(MockToken, AffiliateTokenGatedUpgradeable, YearnTokenVault, YearnRegistry, VipCappedGuestList):
    # Assign accounts
    deployer = accounts[0]
    affiliate = accounts[1]
    manager = accounts[2]
    guardian = accounts[3]
    randomUser1 = accounts[4]
    randomUser2 = accounts[5]
    yearnGovernance = accounts[6]

    namedAccounts = {
        "deployer": deployer, 
        "affiliate": affiliate, 
        "manager": manager, 
        "guardian": guardian,
        "randomUser1": randomUser1,
        "randomUser2": randomUser2,
        "yearnGovernance": yearnGovernance,
    }

    # WBTC (mainnet)
    # wbtc = registry.eth.eth_registry.token_registry.wbtc
    mockToken = deployer.deploy(MockToken)
    mockToken.initialize(
        [randomUser1.address, randomUser2.address],
        [10e18, 10e18],
    )
    print('Token address:', mockToken.address)

    assert mockToken.balanceOf(randomUser1.address) == 10e18
    assert mockToken.balanceOf(randomUser2.address) == 10e18

    # Yearn underlying vault
    vault = deployer.deploy(YearnTokenVault)
    vault.initialize(
        mockToken.address, deployer.address, AddressZero, "YearnWBTC", "vyWBTC"
    )
    print('Vault address:', vault.address)

    # Yearn registry
    yearnRegistry = deployer.deploy(YearnRegistry)
    yearnRegistry.setGovernance(yearnGovernance)
    # Add vault to registry
    yearnRegistry.newRelease(vault.address)
    print('Registry address:', yearnRegistry.address)

    # Deploy and initialize the wrapper contract (deployer -> affiliate)
    wrapper = deployer.deploy(AffiliateTokenGatedUpgradeable)
    wrapper.initialize(
        mockToken.address,
        yearnRegistry.address,
        "BadgerYearnWBTC",
        "bvyWBTC",
        guardian.address,
    )
    print('Wrapper address:', wrapper.address)

    # Deploy the Guestlist contract (deployer -> bouncer)
    guestlist = deployer.deploy(VipCappedGuestList, wrapper.address)

    # Add users to guestlist
    guestlist.setGuests([randomUser1.address, randomUser2.address], [True, False])
    print('Guestlist address:', guestlist.address)

    yield namedtuple('setup', 'mockToken vault yearnRegistry wrapper guestlit namedAccounts')(mockToken, vault, yearnRegistry, wrapper, guestlist, namedAccounts)

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_permissions(setup):
    randomUser1 = setup.namedAccounts['randomUser1']
    randomUser2 = setup.namedAccounts['randomUser2']

    # Set new affiliate from non-affiliate account
    with brownie.reverts():
        setup.wrapper.setAffiliate(randomUser1.address, {"from": randomUser2})
