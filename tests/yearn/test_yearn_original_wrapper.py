from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from tests.conftest import yearnSettTestConfig, badger_single_sett
from collections import namedtuple


@pytest.fixture(scope="module", autouse=True)
def setup(MockToken, AffiliateToken, YearnTokenVault, YearnRegistry):
    # Assign accounts
    deployer = accounts[0]
    affiliate = accounts[1]
    manager = accounts[2]
    guardian = accounts[3]
    randomUser1 = accounts[4]
    randomUser2 = accounts[5]
    randomUser3 = accounts[7]
    yearnGovernance = accounts[6]

    namedAccounts = {
        "deployer": deployer,
        "affiliate": affiliate,
        "manager": manager,
        "guardian": guardian,
        "randomUser1": randomUser1,
        "randomUser2": randomUser2,
        "randomUser3": randomUser3,
        "yearnGovernance": yearnGovernance,
    }

    # WBTC (mainnet)
    mockToken = deployer.deploy(MockToken)
    mockToken.initialize(
        [randomUser1.address, randomUser2.address, randomUser3.address],
        [10e18, 20e18, 10e18],
    )

    assert mockToken.balanceOf(randomUser1.address) == 10e18
    assert mockToken.balanceOf(randomUser2.address) == 20e18
    assert mockToken.balanceOf(randomUser3.address) == 10e18

    # Yearn underlying vault
    vault = deployer.deploy(YearnTokenVault)
    vault.initialize(
        mockToken.address, deployer.address, AddressZero, "YearnWBTC", "vyWBTC"
    )
    vault.setDepositLimit(24e18)

    # Yearn registry
    yearnRegistry = deployer.deploy(YearnRegistry)
    yearnRegistry.setGovernance(yearnGovernance)
    # Add vault to registry
    yearnRegistry.newRelease(vault.address)
    yearnRegistry.endorseVault(vault.address)

    # Deploy and initialize the wrapper contract (deployer -> affiliate)
    wrapper = deployer.deploy(
        AffiliateToken,
        mockToken.address,
        yearnRegistry.address,
        "BadgerYearnWBTC",
        "bvyWBTC",
    )

    yield namedtuple("setup", "mockToken vault yearnRegistry wrapper namedAccounts")(
        mockToken, vault, yearnRegistry, wrapper, namedAccounts
    )


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# @pytest.mark.skip()
def test_deposit_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]
    guardian = setup.namedAccounts["guardian"]
    manager = setup.namedAccounts["manager"]

    if setup.wrapper.bestVault() == setup.vault.address:

        # === Deposit flow === #

        # Approve wrapper as spender of mockToken for users
        setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser3})
        setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
        setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

        # total amount of tokens deposited through wrapper = 0
        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0
        # total supply of wrapper shares = 0
        assert setup.wrapper.totalSupply() == 0

        # = User 2: Has 20 Tokens, deposits 1 = #
        # Random user (from guestlist) deposits 1 Token
        setup.wrapper.deposit(1e18, {"from": randomUser2})
        assert setup.mockToken.balanceOf(randomUser2.address) == 19e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 1e18

        # mockToken balance of vault equal to deposited amount
        assert setup.vault.totalAssets() == 1e18
        assert setup.wrapper.totalAssets() == 1e18

        # wrapper shares are minted for depositor and vault shares are 0 for depositor
        assert setup.vault.balanceOf(randomUser2.address) == 0
        assert setup.wrapper.balanceOf(randomUser2.address) == 1e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18
        print("-- 1st User Deposits 1 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())

        # = User 1: Has 10 Tokens, deposits 10 = #
        # Another random user (from guestlist) deposits all their Tokens (10)
        setup.wrapper.deposit({"from": randomUser1})
        assert setup.mockToken.balanceOf(randomUser1.address) == 0

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 11e18

        # mockToken balance of vault and wrapper equals to net amount
        assert setup.vault.totalAssets() == 11e18
        assert setup.wrapper.totalAssets() == 11e18

        # wrapper shares are minted for depositor and vault shares are 0 for depositor
        assert setup.vault.balanceOf(randomUser1.address) == 0
        assert setup.wrapper.balanceOf(randomUser1.address) == 10e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18
        print("-- 2nd User Deposits 10 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())

        chain.sleep(10000)
        chain.mine(1)

        # === Withdraw flow === #

        # = User 2: Has 19 Tokens, 1 bvyWBTC token, withdraws 0.5 = #
        assert setup.mockToken.balanceOf(randomUser2.address) == 19e18

        setup.wrapper.withdraw(0.5e18, {"from": randomUser2})
        print("-- 1st User withdraws 0.5 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser2.address) == 19.5e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 10.5e18

        # mockToken balance of vault equals to net amount
        assert setup.vault.totalAssets() == 10.5e18
        assert setup.wrapper.totalAssets() == 10.5e18

        # wrapper shares are burned for withdrawer and vault shares are still 0 for withdrawer
        assert setup.vault.balanceOf(randomUser2.address) == 0
        assert setup.wrapper.balanceOf(randomUser2.address) == 0.5e18

        # = User 1: Has 0 Tokens, 10 bvyWBTC token, withdraws all = #
        assert setup.mockToken.balanceOf(randomUser1.address) == 0

        setup.wrapper.withdraw({"from": randomUser1})
        print("-- 2nd User withdraws 10 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser1.address) == 10e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0.5e18

        # mockToken balance of vault equals to net amount
        assert setup.vault.totalAssets() == 0.5e18
        assert setup.wrapper.totalAssets() == 0.5e18

        # wrapper shares are burnt for withdrawer and vault shares are still 0 for withdrawer
        assert setup.vault.balanceOf(randomUser1.address) == 0
        assert setup.wrapper.balanceOf(randomUser1.address) == 0

        # = User 3: Has 10 Tokens, 0 bvyWBTC token, withdraws 1 = #
        # Random user attempts to withdraw 1 token
        # Should revert since user has no tokens on vault
        with brownie.reverts():
            setup.wrapper.withdraw(1e18, {"from": randomUser3})
        # User's token balance remains the same
        assert setup.mockToken.balanceOf(randomUser3.address) == 10e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18

        # = User 2 sends 0.5 byvWBTC to user 3 for withdrawal = #
        setup.wrapper.transfer(randomUser3.address, 0.5e18, {"from": randomUser2})

        assert setup.wrapper.balanceOf(randomUser3.address) == 0.5e18

        # User 3 withdraws using the 0.5 shares received from user 2
        setup.wrapper.withdraw(0.5e18, {"from": randomUser3})
        # mockToken balance of user 3: 10 + 0.5 = 10.5
        assert setup.mockToken.balanceOf(randomUser3.address) == 10.5e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0
