from helpers.time_utils import days
import json
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from collections import namedtuple

with open("merkle/badger-bouncer.json") as f:
    yearnDistribution = json.load(f)

merkleRoot = yearnDistribution["merkleRoot"]

WITHDRAWAL_FEE = 50
DEVIATION_MAX = 50


@pytest.fixture(scope="module", autouse=True)
def setup(
    MockToken,
    AffiliateTokenGatedUpgradeable,
    YearnTokenVault,
    YearnRegistry,
    VipCappedGuestListWrapperUpgradeable,
):
    # Assign accounts
    deployer = accounts[0]
    affiliate = accounts[1]
    manager = accounts[2]
    guardian = accounts[3]
    randomUser1 = accounts[4]
    randomUser2 = accounts[5]
    randomUser3 = accounts[6]
    distributor = accounts[7]
    yearnGovernance = accounts[8]

    namedAccounts = {
        "deployer": deployer,
        "affiliate": affiliate,
        "manager": manager,
        "guardian": guardian,
        "randomUser1": randomUser1,
        "randomUser2": randomUser2,
        "randomUser3": randomUser3,
        "distributor": distributor,
        "yearnGovernance": yearnGovernance,
    }

    # WBTC (mainnet)
    mockToken = deployer.deploy(MockToken)
    mockToken.initialize(
        [
            randomUser1.address,
            randomUser2.address,
            randomUser3.address,
            distributor.address,
        ],
        [10e18, 20e18, 10e18, 10000e18],
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

    # Deploying "experimental" vault
    vaultExp = deployer.deploy(YearnTokenVaultV2)
    vaultExp.initialize(
        mockToken.address, deployer.address, AddressZero, "YearnWBTCExp", "vyWBTCExp"
    )
    vaultExp.setDepositLimit(24e18)

    # Yearn registry
    yearnRegistry = deployer.deploy(YearnRegistry)
    yearnRegistry.setGovernance(yearnGovernance)
    # Add vault to registry
    yearnRegistry.newRelease(vault.address)
    yearnRegistry.endorseVault(vault.address)

    # Deploy and initialize the wrapper contract (deployer -> affiliate)
    wrapper = deployer.deploy(AffiliateTokenGatedUpgradeable)
    wrapper.initialize(
        mockToken.address,
        yearnRegistry.address,
        "BadgerYearnWBTC",
        "bvyWBTC",
        guardian.address,
        True,
        vaultExp.address,
    )

    # Deploy the Guestlist contract (deployer -> bouncer)
    guestlist = deployer.deploy(VipCappedGuestListWrapperUpgradeable)
    guestlist.initialize(wrapper.address)

    # Add users to guestlist
    guestlist.setGuests([randomUser1.address, randomUser2.address], [True, True])
    # Set deposit cap to 15 tokens
    guestlist.setUserDepositCap(15e18)
    guestlist.setTotalDepositCap(50e18)

    yield namedtuple(
        "setup",
        "mockToken vault vaultExp yearnRegistry wrapper guestlist namedAccounts",
    )(mockToken, vault, vaultExp, yearnRegistry, wrapper, guestlist, namedAccounts)


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# @pytest.mark.skip()
def test_permissions(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]
    guardian = setup.namedAccounts["guardian"]
    manager = setup.namedAccounts["manager"]

    # Disabling experimental mode with non-Afiliate reverts
    with brownie.reverts():
        setup.wrapper.disableExperimentalMode({"from": randomUser2})

    with brownie.reverts():
        setup.wrapper.disableExperimentalMode({"from": guardian})

    with brownie.reverts():
        setup.wrapper.disableExperimentalMode({"from": manager})

    # Adding users to guestlist from non-owner account reverts
    with brownie.reverts("Ownable: caller is not the owner"):
        setup.guestlist.setGuests([randomUser3.address], [True], {"from": randomUser2})

    # Setting deposit cap on guestlist from non-owner reverts
    with brownie.reverts("Ownable: caller is not the owner"):
        setup.guestlist.setUserDepositCap(15e18, {"from": randomUser2})

    # Setting guestRoot on guestlist from non-owner reverts
    with brownie.reverts("Ownable: caller is not the owner"):
        setup.guestlist.setGuestRoot(
            "0x00000000000000000000000000000000", {"from": randomUser2}
        )

    # Setting withrdawal fee by non-affiliate account reverts
    with brownie.reverts():
        setup.wrapper.setWithdrawalFee(50, {"from": randomUser2})

    # Setting withrdawal fee higher than allowed reverts
    with brownie.reverts("excessive-withdrawal-fee"):
        setup.wrapper.setWithdrawalFee(10001, {"from": deployer})

    # Setting _maxDeviationThreshold higher than allowed reverts
    with brownie.reverts("excessive-withdrawal-fee"):
        setup.wrapper.setWithdrawalFee(10001, {"from": deployer})

    # Set new affiliate from non-affiliate account reverts
    with brownie.reverts():
        setup.wrapper.setAffiliate(randomUser1.address, {"from": randomUser2})

    # Set new affiliate from affiliate account
    tx = setup.wrapper.setAffiliate(randomUser1.address, {"from": deployer})
    assert len(tx.events) == 1
    assert tx.events[0]["affiliate"] == randomUser1.address

    # Accepting affiliate role from non-pendingAffiliate account reverts
    with brownie.reverts():
        setup.wrapper.acceptAffiliate({"from": randomUser2})

    # Accepting affiliate role from pendingAffiliate account
    tx = setup.wrapper.acceptAffiliate({"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["affiliate"] == randomUser1.address

    # set Guardian from non-affiliate account reverts
    with brownie.reverts():
        setup.wrapper.setGuardian(guardian.address, {"from": randomUser2})

    # set Guardian from previous affiliate account reverts (check for affiliate rights revocation)
    with brownie.reverts():
        setup.wrapper.setGuardian(guardian.address, {"from": deployer})

    # set Guardian from new affiliate account
    tx = setup.wrapper.setGuardian(guardian.address, {"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["guardian"] == guardian.address

    # set Manager from non-affiliate account reverts
    with brownie.reverts():
        setup.wrapper.setManager(manager.address, {"from": randomUser2})

    # set Manager from new affiliate account
    tx = setup.wrapper.setManager(manager.address, {"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["manager"] == manager.address

    # set Guestlist from non-affiliate account reverts
    with brownie.reverts():
        setup.wrapper.setGuestList(setup.guestlist.address, {"from": randomUser2})

    # set Guestlist from new affiliate account
    tx = setup.wrapper.setGuestList(setup.guestlist.address, {"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["guestList"] == setup.guestlist.address

    # pausing contract with unauthorized account reverts
    with brownie.reverts():
        setup.wrapper.pause({"from": randomUser2})

    # pausing contract with guardian
    tx = setup.wrapper.pause({"from": guardian})
    assert len(tx.events) == 1
    assert tx.events[0]["account"] == guardian.address
    assert setup.wrapper.paused() == True

    chain.sleep(10000)
    chain.mine(1)

    # Permforming all write transactions on paused contract reverts
    if setup.wrapper.paused():

        # Approve wrapper as spender of mockToken
        setup.mockToken.approve(setup.wrapper.address, 10e18, {"from": randomUser2})

        # From any user
        with brownie.reverts():
            setup.wrapper.deposit([], {"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.deposit(1e18, [], {"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.withdraw({"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.withdraw(1e18, {"from": randomUser2})

        # From affiliate
        with brownie.reverts():
            setup.wrapper.migrate({"from": randomUser1})

        with brownie.reverts():
            setup.wrapper.migrate(1e18, {"from": randomUser1})

        with brownie.reverts():
            setup.wrapper.migrate(1e18, 1, {"from": randomUser1})

    else:
        pytest.fail("Wrapper not paused")

    # unpausing contract with manager
    tx = setup.wrapper.unpause({"from": manager})
    assert len(tx.events) == 1
    assert tx.events[0]["account"] == manager.address
    assert setup.wrapper.paused() == False

    # pausing contract with manager
    tx = setup.wrapper.pause({"from": manager})
    assert len(tx.events) == 1
    assert tx.events[0]["account"] == manager.address
    assert setup.wrapper.paused() == True

    # unpausing contract with affiliate
    tx = setup.wrapper.unpause({"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["account"] == randomUser1.address
    assert setup.wrapper.paused() == False

    # pausing contract with affiliate
    tx = setup.wrapper.pause({"from": randomUser1})
    assert len(tx.events) == 1
    assert tx.events[0]["account"] == randomUser1.address
    assert setup.wrapper.paused() == True

    # unpausing contract with guardian account reverts
    with brownie.reverts():
        setup.wrapper.unpause({"from": guardian})

    # unpausing contract with unauthorized account reverts
    with brownie.reverts():
        setup.wrapper.unpause({"from": randomUser2})


# @pytest.mark.skip()
def test_deposit_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

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

        # = User 2: Has 20 Tokens, deposits 1, on Guestlist = #
        # Random user (from guestlist) deposits 1 Token
        setup.wrapper.deposit(1e18, [], {"from": randomUser2})
        print("-- 1st User Deposits 1 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser2.address) == 19e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 1e18

        # mockToken balance of vault equal to deposited amount
        assert setup.vault.totalAssets() == 1e18
        assert setup.wrapper.totalAssets() == 1e18

        # wrapper shares are minted for depositor and vault shares are 0 for depositor
        assert setup.vault.balanceOf(randomUser2.address) == 0
        assert setup.wrapper.balanceOf(randomUser2.address) == 1e18

        # Check balance of user within wrapper
        assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 1e18

        # Remaining deposit allowed for User 2: 15 - 1 = 14 mockTokens\
        # Gueslist not adapted to read wrapper usage data
        assert setup.guestlist.remainingUserDepositAllowed(randomUser2.address) == 14e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18

        # = User 1: Has 10 Tokens, deposits 10, on Guestlist = #
        # Another random user (from guestlist) deposits all their Tokens (10)
        setup.wrapper.deposit([], {"from": randomUser1})
        print("-- 2nd User Deposits 10 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser1.address) == 0

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 11e18

        # mockToken balance of vault and wrapper equals to net amount
        assert setup.vault.totalAssets() == 11e18
        assert setup.wrapper.totalAssets() == 11e18

        # wrapper shares are minted for depositor and vault shares are 0 for depositor
        assert setup.vault.balanceOf(randomUser1.address) == 0
        assert setup.wrapper.balanceOf(randomUser1.address) == 10e18

        # Check balance of user within wrapper
        assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 10e18

        # Remaining deposit allowed for User 1: 15 - 10 = 5 mockTokens
        # Gueslist not adapted to read wrapper usage data
        assert setup.guestlist.remainingUserDepositAllowed(randomUser1.address) == 5e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18

        # = User 2: Has 19 Tokens, deposits 15, on Guestlist = #
        # Random user (from guestlist) attempts to deposit 15 tokens with 1 already deposited
        # Should revert since the deposit cap is set to 15 tokens per user
        with brownie.reverts("guest-list-authorization"):
            setup.wrapper.deposit(15e18, [], {"from": randomUser2})
        # User's token balance remains the same
        assert setup.mockToken.balanceOf(randomUser2.address) == 19e18

        # = User 3: Has 10 Tokens, deposits 1, not on Guestlist = #
        # Random user (not from guestlist) attempts to deposit 1 token
        # Should not revert since root is set to 0x0
        setup.wrapper.deposit(1e18, [], {"from": randomUser3})
        print("-- 3rd User Deposits 1 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser3.address) == 9e18

        # = User 1: Has 0 Tokens, deposits 1 and then all, on Guestlist = #
        # Random user (from guestlist) attempts to deposit 1 and then all tokens
        # Should revert since user has no tokens
        assert setup.mockToken.balanceOf(randomUser1.address) == 0
        with brownie.reverts():
            setup.wrapper.deposit(1e18, [], {"from": randomUser1})
        with brownie.reverts():
            setup.wrapper.deposit([], {"from": randomUser1})
        # User's bvyWBTC balance remains the same
        assert setup.wrapper.balanceOf(randomUser1.address) == 10e18

        # Test pricePerShare to equal 1
        assert setup.wrapper.pricePerShare() == 1e18

        # Test shareVaule
        assert setup.wrapper.shareValue(1e18) == 1e18

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

        # Check balance of user within wrapper
        assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0.5e18

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 11.5e18

        # mockToken balance of vault equals to net amount
        assert setup.vault.totalAssets() == 11.5e18
        assert setup.wrapper.totalAssets() == 11.5e18

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

        # Check balance of user within wrapper
        assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0

        assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 1.5e18

        # mockToken balance of vault equals to net amount
        assert setup.vault.totalAssets() == 1.5e18
        assert setup.wrapper.totalAssets() == 1.5e18

        # wrapper shares are burnt for withdrawer and vault shares are still 0 for withdrawer
        assert setup.vault.balanceOf(randomUser1.address) == 0
        assert setup.wrapper.balanceOf(randomUser1.address) == 0

        setup.wrapper.withdraw({"from": randomUser3})
        print("-- 3rd User withdraws 1 --")
        print("Wrapper's PPS:", setup.wrapper.pricePerShare())
        print("Vault's PPS:", setup.vault.pricePerShare())
        assert setup.mockToken.balanceOf(randomUser3.address) == 10e18

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
    else:
        pytest.fail("Vault not added to registry")


# @pytest.mark.skip()
def test_depositFor_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Approve wrapper as spender of mockToken for users
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser3})

    # total amount of tokens deposited through wrapper = 0
    assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0
    # total supply of wrapper shares = 0
    assert setup.wrapper.totalSupply() == 0

    # total wrapper balance of User 1, 2, 3  = 0
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # === Deposit flow === #

    # User 2 (on guestlist) deposits on behalf of User 1 (on guestlist)
    setup.wrapper.depositFor(randomUser1.address, 1e18, [], {"from": randomUser2})

    # total wrapper balance of User 1 = 1 and User 2 = 2
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 1e18
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert setup.wrapper.balanceOf(randomUser1.address) == 1e18
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # User 2 (on guestlist) deposits on behalf of User 3 (not on guestlist)
    setup.wrapper.depositFor(randomUser3.address, 1e18, [], {"from": randomUser2})

    # total wrapper balance of User 1 = 0 and User 2 = 1
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 1e18
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert setup.wrapper.balanceOf(randomUser3.address) == 1e18
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # === Withdraw flow === #

    # Reverts when User 2 tries to withdraw
    with brownie.reverts():
        setup.wrapper.withdraw(1e18, {"from": randomUser2})

    # User 1 withdraws using their received shares
    setup.wrapper.withdraw({"from": randomUser1})
    # User 1 gets 1 mocktoken in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser1.address) == 0
    assert setup.mockToken.balanceOf(randomUser1.address) == 11e18

    # User 3 withdraws using their received shares
    setup.wrapper.withdraw({"from": randomUser3})
    # User 3 gets 1 mocktoken in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser3.address) == 0
    assert setup.mockToken.balanceOf(randomUser3.address) == 11e18

    # Wrapper balance of all users is zero
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # mockToken balance of User 2 is 18 (20 - 2 = 18)
    assert setup.mockToken.balanceOf(randomUser2.address) == 18e18

    # === depositFor wihout merkle verification === #

    # Add merkleRoot to Guestlist for verification
    setup.guestlist.setGuestRoot(merkleRoot)

    # User 3 (not guestlist) deposits on behalf of User 2 without proof and reverts
    with brownie.reverts():
        setup.wrapper.depositFor(randomUser2.address, 1e18, {"from": randomUser3})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # User 3 (not on guestlist) deposits on behalf of User 2 without proof
    setup.wrapper.depositFor(randomUser2.address, 1e18, {"from": randomUser3})

    # total wrapper balance of User 1 = 0 and User 2 = 1
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 1e18
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert setup.wrapper.balanceOf(randomUser2.address) == 1e18
    assert setup.wrapper.balanceOf(randomUser3.address) == 0


# @pytest.mark.skip()
def test_deposit_withdraw_fees_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set withdrawal fee
    tx = setup.wrapper.setWithdrawalFee(50, {"from": deployer})
    assert len(tx.events) == 1
    assert tx.events[0]["withdrawalFee"] == 50

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

        # Random user deposits 15 Token
        setup.wrapper.deposit(15e18, [], {"from": randomUser2})
        assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 15e18
        assert setup.mockToken.balanceOf(randomUser2.address) == 5e18

        # === Withdraw flow === #

        # Affiliate account mockToken balance is zero
        assert setup.mockToken.balanceOf(deployer.address) == 0

        # Random user withdraws 10 tokens
        tx = setup.wrapper.withdraw(10e18, {"from": randomUser2})
        assert tx.events["WithdrawalFee"]["recipient"] == deployer.address
        assert tx.events["WithdrawalFee"]["amount"] == 0.05e18

        # Affiliate account mockToken balance is 0.5% of 10 mockTokens = 0.05 mockTokens
        assert setup.mockToken.balanceOf(deployer.address) == 0.05e18

        # Random user's mockToken balance is 5 + (10-0.05) = 14.95 mockTokens
        assert setup.mockToken.balanceOf(randomUser2.address) == 14.95e18

        # Random user's wrapper balance is 5
        assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 5e18


# @pytest.mark.skip()
def test_deposit_limit(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Deposit 10 tokens from first user
    setup.wrapper.deposit(10e18, [], {"from": randomUser1})
    # Depositing 15 more tokens reverts because vault limit is 24 tokens
    with brownie.reverts():
        setup.wrapper.deposit(15e18, [], {"from": randomUser2})


# @pytest.mark.skip()
def test_migrate_all_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e18, [], {"from": randomUser1})
    setup.wrapper.deposit(10e18, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.mockToken.address,
        deployer.address,
        AddressZero,
        "YearnWBTCV2",
        "vyWBTCV2",
    )
    vaultV2.setDepositLimit(24e18)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # User 2 deposits another 5 tokens into new vault
    setup.wrapper.deposit(5e18, [], {"from": randomUser2})

    # Vault should have 20 mockTokens
    assert setup.vault.totalAssets() == 20e18

    # VaultV2 should have 5 mockTokens
    assert vaultV2.totalAssets() == 5e18

    # User 2 withdraws all from wrapper (should withdraw from oldest vault first: 15 tokens)
    assert setup.mockToken.balanceOf(randomUser2.address) == 5e18
    assert setup.wrapper.balanceOf(randomUser2.address) == 15e18

    setup.wrapper.withdraw({"from": randomUser2})

    assert setup.mockToken.balanceOf(randomUser2.address) == 20e18
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # Vault should have 5 mockTokens (Withdraws from old vault first)
    assert setup.vault.totalAssets() == 5e18

    # VaultV2 should have 5 mockTokens
    assert vaultV2.totalAssets() == 5e18

    # Balance of User 1 should be 10 (split among both vaults)
    assert setup.wrapper.balanceOf(randomUser1.address) == 10e18

    affiliateBalanceBefore = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer User 1's 5 tokens from Vault to VaultV2
    setup.wrapper.migrate()

    affiliateBalanceAfter = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Vault should have 0 mockTokens
    assert setup.vault.totalAssets() == 0e18

    # VaultV2 should have 10 mockTokens
    assert vaultV2.totalAssets() == 10e18

    # User 1 withdraws all from wrapper (should withdraw from VaultV2: 10 tokens)
    assert setup.mockToken.balanceOf(randomUser1.address) == 0
    assert setup.wrapper.balanceOf(randomUser1.address) == 10e18

    setup.wrapper.withdraw({"from": randomUser1})

    assert setup.mockToken.balanceOf(randomUser1.address) == 10e18
    assert setup.wrapper.balanceOf(randomUser1.address) == 0

    # VaultV2 should have 0 mockTokens
    assert vaultV2.totalAssets() == 0

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


# @pytest.mark.skip()
def test_migrate_amount_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e18, [], {"from": randomUser1})
    setup.wrapper.deposit(10e18, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.mockToken.address,
        deployer.address,
        AddressZero,
        "YearnWBTCV2",
        "vyWBTCV2",
    )
    vaultV2.setDepositLimit(24e18)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # Vault should have 20 mockTokens
    assert setup.vault.totalAssets() == 20e18

    # VaultV2 should have 0 mockTokens
    assert vaultV2.totalAssets() == 0

    affiliateBalanceBefore = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer given amount from Vault to VaultV2
    setup.wrapper.migrate(5e18)

    affiliateBalanceAfter = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Vault should have 0 mockTokens
    assert setup.vault.totalAssets() == 15e18

    # VaultV2 should have 10 mockTokens
    assert vaultV2.totalAssets() == 5e18

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


# @pytest.mark.skip()
def test_migrate_amount_margin_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e18, [], {"from": randomUser1})
    setup.wrapper.deposit(10e18, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.mockToken.address,
        deployer.address,
        AddressZero,
        "YearnWBTCV2",
        "vyWBTCV2",
    )
    vaultV2.setDepositLimit(24e18)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # Vault should have 20 mockTokens
    assert setup.vault.totalAssets() == 20e18

    # VaultV2 should have 0 mockTokens
    assert vaultV2.totalAssets() == 0

    affiliateBalanceBefore = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer given amount from Vault to VaultV2 with loss margin
    setup.wrapper.migrate(5e18, 1e18)

    affiliateBalanceAfter = setup.mockToken.balanceOf(setup.wrapper.affiliate())

    # Vault should have 15 mockTokens
    assert setup.vault.totalAssets() == 15e18

    # VaultV2 should have 5 mockTokens
    assert vaultV2.totalAssets() == 5e18

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


# @pytest.mark.skip()
def test_experimental_mode(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Experimental mode is set at the wrapper's initialization
    # bestVault should be the experimental vault
    assert setup.wrapper.bestVault() == setup.vaultExp.address
    assert setup.wrapper.allVaults() == [setup.vaultExp.address]

    # Total amount of assets on vaultExp should be 0
    assert setup.vaultExp.totalAssets() == 0

    # === Deposit flow === #

    # Deposit 5 tokens from User 2 to wrapper
    setup.wrapper.deposit(5e18, [], {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 5e18
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 5e18

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e18
    print("-- 1st Deposit --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # Deposit all tokens from User 1 to wrapper
    setup.wrapper.deposit([], {"from": randomUser1})
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 10e18
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 15e18

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e18
    print("-- 2nd Deposit --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    chain.sleep(10000)
    chain.mine(1)

    # === Withdraw flow === #

    # Withdraws 2.5 tokens from User 2 to wrapper
    setup.wrapper.withdraw(2.5e18, {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 2.5e18
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 12.5e18

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e18
    print("-- 1st Withdraw --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # Deposit all tokens from User 1 to wrapper
    setup.wrapper.withdraw({"from": randomUser1})
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 2.5e18

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e18
    print("-- 2nd Withdraw --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # User attempts to withdraw more assets than the available on the vaultExp and reverts
    with brownie.reverts():
        setup.wrapper.withdraw(16e18, {"from": randomUser2})

    # === Disable experimental mode === #

    setup.wrapper.disableExperimentalMode({"from": deployer})

    chain.sleep(10000)
    chain.mine(1)

    # bestVault should be the registry's latest vault
    assert setup.wrapper.bestVault() == setup.vault.address
    assert setup.wrapper.allVaults() == [setup.vault.address]
    assert setup.vault.totalAssets() == 0

    # User attempts to withdraw their 2.5 tokens left on experimental vault but this
    setup.wrapper.balanceOf(randomUser2.address) == 2.5e18
    setup.mockToken.balanceOf(randomUser2.address) == 17.5e18
    setup.wrapper.withdraw(2.5e18, {"from": randomUser2})
    setup.mockToken.balanceOf(randomUser2.address) == 17.5e18
    setup.wrapper.balanceOf(randomUser2.address) == 0

    # Deposit 5 tokens from User 2 to wrapper
    setup.wrapper.deposit(5e18, [], {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 5e18
    assert setup.vault.totalAssets() == 5e18
    assert setup.vaultExp.totalAssets() == 2.5e18


# @pytest.mark.skip()
def test_gustlist_authentication(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    distributor = setup.namedAccounts["distributor"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Remove merkle proof verification from Gueslist
    print("Merkleroot:", merkleRoot)
    setup.guestlist.setGuestRoot(merkleRoot)

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    users = [
        web3.toChecksumAddress("0x8107b00171a02f83D7a17f62941841C29c3ae60F"),
        web3.toChecksumAddress("0x716722C80757FFF31DA3F3C392A1736b7cfa3A3e"),
        web3.toChecksumAddress("0xCf7760E00327f608543c88526427b35049b58984"),
    ]

    totalDeposits = 0

    # Test depositing without being on the predefined gueslist with a few users
    for user in users:
        accounts.at(user, force=True)

        claim = yearnDistribution["claims"][user]
        proof = claim["proof"]

        # Transfers 1 token to current user
        setup.mockToken.transfer(user, 1e18, {"from": distributor})

        # Approve wrapper to transfer user's token
        setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": user})

        # User deposits 1 token through wrapper
        assert setup.wrapper.totalWrapperBalance(user) == 0
        setup.wrapper.deposit(1e18, proof, {"from": user})

        assert setup.wrapper.totalWrapperBalance(user) == 1e18

        totalDeposits = totalDeposits + 1e18

        assert setup.wrapper.totalAssets() == totalDeposits

    users = [
        web3.toChecksumAddress("0xb43b8B43dE2e59A2B44caa2910E31a4E835d4068"),
        web3.toChecksumAddress("0x70eF271e741AA071018A57B6E121fe981409a16D"),
        web3.toChecksumAddress("0x71535AAe1B6C0c51Db317B54d5eEe72d1ab843c1"),
    ]

    # Test depositing after provingInvitation of a few users
    for user in users:
        accounts.at(user, force=True)

        claim = yearnDistribution["claims"][user]
        proof = claim["proof"]

        # Transfers 1 token to current user
        setup.mockToken.transfer(user, 1e18, {"from": distributor})

        # Approve wrapper to transfer user's token
        setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": user})

        tx = setup.guestlist.proveInvitation(user, proof)
        assert tx.events[0]["guestRoot"] == merkleRoot
        assert tx.events[0]["account"] == user

        # User deposits 1 token through wrapper (without proof)
        assert setup.wrapper.totalWrapperBalance(user) == 0
        setup.wrapper.deposit(1e18, [], {"from": user})

        assert setup.wrapper.totalWrapperBalance(user) == 1e18

    # Test depositing with user on Gueslist but with no merkle proof

    # Approve wrapper to transfer user's token
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    setup.wrapper.deposit(1e18, [], {"from": randomUser1})
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 1e18

    # Test depositing with user not on Gueslist and with no merkle proof

    # Approve wrapper to transfer user's token
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser3})

    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(1e18, [], {"from": randomUser3})
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0


# @pytest.mark.skip()
def test_initial_deposit_conditions(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser2})
    setup.mockToken.approve(setup.wrapper.address, 100e18, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # User deposits to vault through wrapper
    setup.wrapper.deposit(5e18, [], {"from": randomUser2})

    # Deploying new version of vault
    vaultPPS = deployer.deploy(YearnTokenVault_PPS)
    vaultPPS.initialize(
        setup.mockToken.address,
        deployer.address,
        AddressZero,
        "YearnWBTCV2",
        "vyWBTCV2",
    )
    vaultPPS.setDepositLimit(24e18)
    # Set a PPS > 1 for the underlying vault
    vaultPPS.setPricePerShare(2e18)

    assert vaultPPS.pricePerShare() == 2e18

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultPPS.address)
    setup.yearnRegistry.endorseVault(vaultPPS.address)

    # Check that vaultPPS is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultPPS.address

    # User 2 deposits another 5 tokens into new vault should revert because PPS > 1
    # with brownie.reverts():
    # setup.wrapper.deposit(5e18, [], {"from": randomUser2})
