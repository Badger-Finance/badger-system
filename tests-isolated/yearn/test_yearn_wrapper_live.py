from helpers.time_utils import days
import json
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from helpers.registry.artifacts import artifacts
from collections import namedtuple

with open("merkle/badger-bouncer.json") as f:
    yearnDistribution = json.load(f)

merkleRoot = yearnDistribution["merkleRoot"]

WITHDRAWAL_FEE = 50
DEVIATION_MAX = 50

TOLERANCE = 11


@pytest.fixture(scope="module", autouse=True)
def setup(
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

    # Yearn governance account
    yearnGovernance = accounts.at(
        "0xfeb4acf3df3cdea7399794d0869ef76a6efaff52", force=True
    )

    # WBTC owner account
    wbtcOwner = accounts.at("0xca06411bd7a7296d7dbdd0050dfc846e95febeb7", force=True)

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
        "wbtcOwner": wbtcOwner,
    }

    # WBTC
    abi = artifacts.wbtc["wbtc"]["abi"]
    wbtc = Contract.from_abi("WBTC", registry.tokens.wbtc, abi, wbtcOwner)
    print(wbtc.name() + " fetched")

    assert wbtc.owner() == wbtcOwner.address

    # Deployer mints WBTC tokens for users
    wbtc.mint(randomUser1.address, 10e8)
    wbtc.mint(randomUser2.address, 20e8)
    wbtc.mint(randomUser3.address, 10e8)
    wbtc.mint(distributor.address, 1000e8)

    assert wbtc.balanceOf(randomUser1.address) == 10e8
    assert wbtc.balanceOf(randomUser2.address) == 20e8
    assert wbtc.balanceOf(randomUser3.address) == 10e8
    assert wbtc.balanceOf(distributor.address) == 1000e8

    # Yearn underlying vault (yvWBTC)
    yvwbtc = interface.VaultAPI("0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E")
    print(yvwbtc.name() + " fetched")

    # Yearn registry
    yearnRegistry = deployer.deploy(YearnRegistry)
    yearnRegistry.setGovernance(yearnGovernance.address)
    # No need to add vault since we will test in experimental mode

    # Deploy and initialize the wrapper contract (deployer -> affiliate)
    wrapper = deployer.deploy(AffiliateTokenGatedUpgradeable)
    wrapper.initialize(
        wbtc.address,
        yearnRegistry.address,
        "BadgerYearnWBTC",
        "byvwbtc",
        guardian.address,
        True,
        yvwbtc.address,
    )

    # Deploy the Guestlist contract (deployer -> bouncer)
    guestlist = deployer.deploy(VipCappedGuestListWrapperUpgradeable)
    guestlist.initialize(wrapper.address)

    # Add users to guestlist
    guestlist.setGuests([randomUser1.address, randomUser2.address], [True, True])
    # Set deposit cap to 15 tokens
    guestlist.setUserDepositCap(15e8)
    guestlist.setTotalDepositCap(50e8)

    yield namedtuple(
        "setup", "wbtc yvwbtc yearnRegistry wrapper guestlist namedAccounts"
    )(wbtc, yvwbtc, yearnRegistry, wrapper, guestlist, namedAccounts)


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
        setup.guestlist.setUserDepositCap(15e8, {"from": randomUser2})

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

        # Approve wrapper as spender of wbtc
        setup.wbtc.approve(setup.wrapper.address, 10e8, {"from": randomUser2})

        # From any user
        with brownie.reverts():
            setup.wrapper.deposit([], {"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.deposit(1e8, [], {"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.withdraw({"from": randomUser2})

        with brownie.reverts():
            setup.wrapper.withdraw(1e8, {"from": randomUser2})

        # From affiliate
        with brownie.reverts():
            setup.wrapper.migrate({"from": randomUser1})

        with brownie.reverts():
            setup.wrapper.migrate(1e8, {"from": randomUser1})

        with brownie.reverts():
            setup.wrapper.migrate(1e8, 1, {"from": randomUser1})

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


@pytest.mark.skip()
def test_deposit_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # === Deposit flow === #

    # Approve wrapper as spender of wbtc for users
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser3})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # total amount of wbtc deposited through wrapper = 0
    assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0
    # total supply of wrapper shares = 0
    assert setup.wrapper.totalSupply() == 0

    # = User 2: Has 20 wbtc, deposits 1, on Guestlist = #
    # Random user (from guestlist) deposits 1 Token
    setup.wrapper.deposit(1e8, [], {"from": randomUser2})
    print("-- 1st User Deposits 1 --")
    assert setup.wbtc.balanceOf(randomUser2.address) == 19e8

    # Check balance of user within wrapper is within tolerance
    assert abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 1e8) < TOLERANCE

    # total amount of wbtc deposited through wrapper = ~1
    assert abs(setup.wrapper.totalVaultBalance(setup.wrapper.address) - 1e8) < TOLERANCE

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert setup.yvwbtc.balanceOf(randomUser2.address) == 0
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser2.address)
            - (1e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        < TOLERANCE
    )

    # Remaining deposit allowed for User 2: 15 - 1 = 14 wbtcs
    assert (
        abs(setup.guestlist.remainingUserDepositAllowed(randomUser2.address) - 14e8)
        < TOLERANCE
    )

    chain.sleep(86400)
    chain.mine(1)

    # = User 1: Has 10 wbtc, deposits 10, on Guestlist = #
    # Another random user (from guestlist) deposits all their Tokens (10)
    setup.wrapper.deposit([], {"from": randomUser1})
    print("-- 2nd User Deposits 10 --")
    assert setup.wbtc.balanceOf(randomUser1.address) == 0

    # Check balance of user within wrapper is within tolerance
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser1.address) - 10e8) <= TOLERANCE
    )

    # total amount of wbtc deposited through wrapper = ~11
    assert (
        abs(setup.wrapper.totalVaultBalance(setup.wrapper.address) - 11e8) <= TOLERANCE
    )

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert setup.yvwbtc.balanceOf(randomUser1.address) == 0
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser1.address)
            - (10e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )

    # Remaining deposit allowed for User 2: 15 - 10 = 5 wbtcs
    assert (
        abs(setup.guestlist.remainingUserDepositAllowed(randomUser1.address) - 5e8)
        <= TOLERANCE
    )

    chain.sleep(86400)
    chain.mine(1)

    # = User 2: Has 19 wbtc, deposits 15, on Guestlist = #
    # Random user (from guestlist) attempts to deposit 15 tokens with 1 already deposited
    # Should revert since the deposit cap is set to 15 tokens per user
    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(15e8, [], {"from": randomUser2})
    # User's token balance remains the same
    assert setup.wbtc.balanceOf(randomUser2.address) == 19e8

    # = User 3: Has 10 wbtc, deposits 1, not on Guestlist = #
    # Random user (not from guestlist) attempts to deposit 1 token
    # Should not revert since root is set to 0x0
    setup.wrapper.deposit(1e8, [], {"from": randomUser3})
    print("-- 3rd User Deposits 1 --")
    assert setup.wbtc.balanceOf(randomUser3.address) == 9e8

    # Check balance of user within wrapper is within tolerance
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser3.address) - 1e8) <= TOLERANCE
    )

    # total amount of wbtc deposited through wrapper = ~11
    assert (
        abs(setup.wrapper.totalVaultBalance(setup.wrapper.address) - 12e8) <= TOLERANCE
    )

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert setup.yvwbtc.balanceOf(randomUser3.address) == 0
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser3.address)
            - (1e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )

    # Remaining deposit allowed for User 2: 15 - 10 = 5 wbtcs
    assert (
        abs(setup.guestlist.remainingUserDepositAllowed(randomUser3.address) - 14e8)
        <= TOLERANCE
    )

    # = User 1: Has 0 wbtc, deposits 1 and then all, on Guestlist = #
    # Random user (from guestlist) attempts to deposit 1 and then all tokens
    # Should revert since user has no tokens
    assert setup.wbtc.balanceOf(randomUser1.address) == 0
    with brownie.reverts():
        setup.wrapper.deposit(1e8, [], {"from": randomUser1})
    with brownie.reverts():
        setup.wrapper.deposit([], {"from": randomUser1})
    # User's bvyWBTC balance remains the same
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser1.address)
            - (10e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )

    chain.sleep(86400)
    chain.mine(1)

    # === Withdraw flow === #

    # = User 2: Has 19 wbtc, withdraws half their shares = #
    assert setup.wbtc.balanceOf(randomUser2.address) == 19e8
    shares = setup.wrapper.balanceOf(randomUser2.address) / 2

    setup.wrapper.withdraw(shares, {"from": randomUser2})
    print("-- 1st User withdraws " + str(shares) + " shares --")
    print(
        "Withdrew "
        + str(abs(19e8 - setup.wbtc.balanceOf(randomUser2.address)) / 1e8)
        + " wbtc"
    )
    assert setup.wbtc.balanceOf(randomUser2.address) - 19.5e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser2.address) <= 19.5e8

    # Check balance of user within wrapper
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 0.5e8) <= TOLERANCE
    )

    # total amount of wbtc deposited through wrapper = ~11.5
    assert (
        abs(setup.wrapper.totalVaultBalance(setup.wrapper.address) - 11.5e8)
        <= TOLERANCE
    )

    # wrapper shares are burned for withdrawer and yvwbtc shares are still 0 for withdrawer
    assert setup.yvwbtc.balanceOf(randomUser2.address) == 0
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser2.address)
            - (0.5e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )

    chain.sleep(86400)
    chain.mine(1)

    # = User 1: Has 0 Tokens, withdraws all = #
    assert setup.wbtc.balanceOf(randomUser1.address) == 0
    shares = setup.wrapper.balanceOf(randomUser1.address)

    setup.wrapper.withdraw({"from": randomUser1})
    print("-- 2nd User withdraws " + str(shares) + " shares --")
    print("Withdrew " + str(setup.wbtc.balanceOf(randomUser1.address) / 1e8) + " wbtc")
    assert setup.wbtc.balanceOf(randomUser1.address) - 10e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser1.address) <= 10e8

    # Check balance of user within wrapper
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0

    # total amount of wbtc deposited through wrapper left = ~1.5
    assert (
        abs(setup.wrapper.totalVaultBalance(setup.wrapper.address) - 1.5e8) <= TOLERANCE
    )

    # wrapper shares are burned for withdrawer and yvwbtc shares are still 0 for withdrawer
    assert setup.yvwbtc.balanceOf(randomUser1.address) == 0
    assert setup.wrapper.balanceOf(randomUser1.address) == 0

    chain.sleep(86400)
    chain.mine(1)

    # = User 3: Has 9 wbtc, withdraws all = #
    assert setup.wbtc.balanceOf(randomUser3.address) == 9e8
    shares = setup.wrapper.balanceOf(randomUser3.address)

    setup.wrapper.withdraw({"from": randomUser3})
    print("-- 3rd User withdraws " + str(shares) + " shares --")
    print(
        "Withdrew "
        + str(abs(9e8 - setup.wbtc.balanceOf(randomUser3.address)) / 1e8)
        + " wbtc"
    )
    assert setup.wbtc.balanceOf(randomUser3.address) - 10e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10e8

    # = User 3: Has 10 wbtc, withdraws 1 share= #
    # Random user attempts to withdraw 1 share
    # Should revert since user has no tokens on yvwbtc
    with brownie.reverts():
        setup.wrapper.withdraw(1e8, {"from": randomUser3})
    # User's token balance remains the same
    assert abs(setup.wbtc.balanceOf(randomUser3.address) - 10e8) <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10e8

    chain.sleep(86400)
    chain.mine(1)

    # = User 2 sends remaining half of shares to user 3 for withdrawal = #
    shares = setup.wrapper.balanceOf(randomUser2.address)
    setup.wrapper.transfer(randomUser3.address, shares, {"from": randomUser2})

    assert setup.wrapper.balanceOf(randomUser3.address) == shares

    # User 3 withdraws using the shares received from user 2, equivalent to 0.5
    setup.wrapper.withdraw(shares, {"from": randomUser3})
    print("-- 3rd User withdraws " + str(shares) + " shares --")
    print(
        "Withdrew "
        + str(abs(10e8 - setup.wbtc.balanceOf(randomUser3.address)) / 1e8)
        + " wbtc"
    )
    # wbtc balance of user 3: 10 + 0.5 = ~10.5
    assert setup.wbtc.balanceOf(randomUser3.address) - 10.5e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10.5e8

    assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0

    assert setup.wrapper.balanceOf(randomUser1.address) == 0
    assert setup.wrapper.balanceOf(randomUser2.address) == 0
    assert setup.wrapper.balanceOf(randomUser3.address) == 0


@pytest.mark.skip()
def test_depositFor_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Set total deposit cap
    setup.guestlist.setTotalDepositCap(50e8)

    # Approve wrapper as spender of wbtc for users
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser3})

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
    setup.wrapper.depositFor(randomUser1.address, 1e8, [], {"from": randomUser2})

    # total wrapper balance of User 1 = 1 and User 2 = 2
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser1.address) - 1e8) <= TOLERANCE
    )
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser1.address)
            - (1e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # User 2 (on guestlist) deposits on behalf of User 3 (not on guestlist)
    setup.wrapper.depositFor(randomUser3.address, 1e8, [], {"from": randomUser2})

    # total wrapper balance of User 1 = 0 and User 2 = 1
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser3.address) - 1e8) <= TOLERANCE
    )
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser3.address)
            - (1e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # === Withdraw flow === #

    # Reverts when User 2 tries to withdraw
    with brownie.reverts():
        setup.wrapper.withdraw(0.1e8, {"from": randomUser2})

    # User 1 withdraws using their received shares
    setup.wrapper.withdraw({"from": randomUser1})
    # User 1 gets 1 wbtc in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser1.address) == 0
    assert setup.wbtc.balanceOf(randomUser1.address) - 11e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser1.address) <= 11e8

    # User 3 withdraws using their received shares
    setup.wrapper.withdraw({"from": randomUser3})
    # User 3 gets 1 wbtc in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser3.address) == 0
    assert setup.wbtc.balanceOf(randomUser3.address) - 11e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 11e8

    # Wrapper balance of all users is zero
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # wbtc balance of User 2 is 18 (20 - 2 = 18)
    assert setup.wbtc.balanceOf(randomUser2.address) == 18e8

    # === depositFor wihout merkle verification === #

    # Add merkleRoot to Guestlist for verification
    setup.guestlist.setGuestRoot(merkleRoot)

    # User 3 (not guestlist) deposits on behalf of User 2 without proof and reverts
    with brownie.reverts():
        setup.wrapper.depositFor(randomUser2.address, 1e8, {"from": randomUser3})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # User 3 (not on guestlist) deposits on behalf of User 2 without proof
    setup.wrapper.depositFor(randomUser2.address, 1e8, {"from": randomUser3})

    # total wrapper balance of User 1 = 0 and User 2 = 1
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 1e8) <= TOLERANCE
    )
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert (
        abs(
            setup.wrapper.balanceOf(randomUser2.address)
            - (1e8 / setup.wrapper.pricePerShare()) * 1e8
        )
        <= TOLERANCE
    )
    assert setup.wrapper.balanceOf(randomUser3.address) == 0


@pytest.mark.skip()
def test_deposit_withdraw_fees_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Set total deposit cap
    setup.guestlist.setTotalDepositCap(50e8)

    # Set withdrawal fee
    tx = setup.wrapper.setWithdrawalFee(50, {"from": deployer})
    assert len(tx.events) == 1
    assert tx.events[0]["withdrawalFee"] == 50

    # === Deposit flow === #

    # Approve wrapper as spender of wbtc for users
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser3})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # total amount of wbtc deposited through wrapper = 0
    assert setup.wrapper.totalVaultBalance(setup.wrapper.address) == 0
    # total supply of wrapper shares = 0
    assert setup.wrapper.totalSupply() == 0

    # Random user deposits 15 wbtc
    setup.wrapper.deposit(15e8, [], {"from": randomUser2})
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 15e8) <= TOLERANCE
    )
    assert setup.wbtc.balanceOf(randomUser2.address) == 5e8

    # === Withdraw flow === #

    # Affiliate account wbtc balance is zero
    assert setup.wbtc.balanceOf(deployer.address) == 0

    # Random user withdraws 2/3 of their shares (eq. to a 10wbtc deposit)
    shares = (2 * setup.wrapper.balanceOf(randomUser2.address)) / 3

    tx = setup.wrapper.withdraw(shares, {"from": randomUser2})
    assert tx.events["WithdrawalFee"]["recipient"] == deployer.address
    assert tx.events["WithdrawalFee"]["amount"] - 0.05e8 <= TOLERANCE

    # Affiliate account wbtc balance is 0.5% of 10 wbtcs = ~0.05 wbtc
    assert setup.wbtc.balanceOf(deployer.address) - 0.05e8 <= TOLERANCE
    assert setup.wbtc.balanceOf(deployer.address) <= 0.05e8

    # Random user's wbtc balance is 5 + (10-0.05) = 14.95 wbtcs
    assert setup.wbtc.balanceOf(randomUser2.address) == 14.95e8

    # Random user's wrapper balance is 5
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 5e8) <= TOLERANCE
    )


@pytest.mark.skip()
def test_migrate_all_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e8, [], {"from": randomUser1})
    setup.wrapper.deposit(10e8, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.wbtc.address, deployer.address, AddressZero, "YearnWBTCV2", "vyWBTCV2"
    )
    vaultV2.setDepositLimit(24e8)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # User 2 deposits another 5 tokens into new vault
    setup.wrapper.deposit(5e8, [], {"from": randomUser2})

    # Vault should have 20 wbtcs
    assert setup.vault.totalAssets() == 20e8

    # VaultV2 should have 5 wbtcs
    assert vaultV2.totalAssets() == 5e8

    # User 2 withdraws all from wrapper (should withdraw from oldest vault first: 15 tokens)
    assert setup.wbtc.balanceOf(randomUser2.address) == 5e8
    assert setup.wrapper.balanceOf(randomUser2.address) == 15e8

    setup.wrapper.withdraw({"from": randomUser2})

    assert setup.wbtc.balanceOf(randomUser2.address) == 20e8
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # Vault should have 5 wbtcs (Withdraws from old vault first)
    assert setup.vault.totalAssets() == 5e8

    # VaultV2 should have 5 wbtcs
    assert vaultV2.totalAssets() == 5e8

    # Balance of User 1 should be 10 (split among both vaults)
    assert setup.wrapper.balanceOf(randomUser1.address) == 10e8

    affiliateBalanceBefore = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer User 1's 5 tokens from Vault to VaultV2
    setup.wrapper.migrate()

    affiliateBalanceAfter = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Vault should have 0 wbtcs
    assert setup.vault.totalAssets() == 0e8

    # VaultV2 should have 10 wbtcs
    assert vaultV2.totalAssets() == 10e8

    # User 1 withdraws all from wrapper (should withdraw from VaultV2: 10 tokens)
    assert setup.wbtc.balanceOf(randomUser1.address) == 0
    assert setup.wrapper.balanceOf(randomUser1.address) == 10e8

    setup.wrapper.withdraw({"from": randomUser1})

    assert setup.wbtc.balanceOf(randomUser1.address) == 10e8
    assert setup.wrapper.balanceOf(randomUser1.address) == 0

    # VaultV2 should have 0 wbtcs
    assert vaultV2.totalAssets() == 0

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


@pytest.mark.skip()
def test_migrate_amount_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e8, [], {"from": randomUser1})
    setup.wrapper.deposit(10e8, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.wbtc.address, deployer.address, AddressZero, "YearnWBTCV2", "vyWBTCV2"
    )
    vaultV2.setDepositLimit(24e8)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # Vault should have 20 wbtcs
    assert setup.vault.totalAssets() == 20e8

    # VaultV2 should have 0 wbtcs
    assert vaultV2.totalAssets() == 0

    affiliateBalanceBefore = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer given amount from Vault to VaultV2
    setup.wrapper.migrate(5e8)

    affiliateBalanceAfter = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Vault should have 0 wbtcs
    assert setup.vault.totalAssets() == 15e8

    # VaultV2 should have 10 wbtcs
    assert vaultV2.totalAssets() == 5e8

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


@pytest.mark.skip()
def test_migrate_amount_margin_flow(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # Deposit tokens from User 1 and 2 to current bestVault
    setup.wrapper.deposit(10e8, [], {"from": randomUser1})
    setup.wrapper.deposit(10e8, [], {"from": randomUser2})

    # Check that vault is current 'bestVault'
    assert setup.wrapper.bestVault() == setup.vault.address

    # Deploying new version of vault
    vaultV2 = deployer.deploy(YearnTokenVaultV2)
    vaultV2.initialize(
        setup.wbtc.address, deployer.address, AddressZero, "YearnWBTCV2", "vyWBTCV2"
    )
    vaultV2.setDepositLimit(24e8)

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultV2.address)
    setup.yearnRegistry.endorseVault(vaultV2.address)

    # Check that vaultV2 is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultV2.address

    # Vault should have 20 wbtcs
    assert setup.vault.totalAssets() == 20e8

    # VaultV2 should have 0 wbtcs
    assert vaultV2.totalAssets() == 0

    affiliateBalanceBefore = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Migrate: should transfer given amount from Vault to VaultV2 with loss margin
    setup.wrapper.migrate(5e8, 1e8)

    affiliateBalanceAfter = setup.wbtc.balanceOf(setup.wrapper.affiliate())

    # Vault should have 15 wbtcs
    assert setup.vault.totalAssets() == 15e8

    # VaultV2 should have 5 wbtcs
    assert vaultV2.totalAssets() == 5e8

    # Affiliate token balance should not change
    assert affiliateBalanceAfter == affiliateBalanceBefore


@pytest.mark.skip()
def test_experimental_mode(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

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
    setup.wrapper.deposit(5e8, [], {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 5e8
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 5e8

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e8
    print("-- 1st Deposit --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # Deposit all tokens from User 1 to wrapper
    setup.wrapper.deposit([], {"from": randomUser1})
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 10e8
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 15e8

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e8
    print("-- 2nd Deposit --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    chain.sleep(10000)
    chain.mine(1)

    # === Withdraw flow === #

    # Withdraws 2.5 tokens from User 2 to wrapper
    setup.wrapper.withdraw(2.5e8, {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 2.5e8
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 12.5e8

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e8
    print("-- 1st Withdraw --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # Deposit all tokens from User 1 to wrapper
    setup.wrapper.withdraw({"from": randomUser1})
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.vault.totalAssets() == 0
    assert setup.vaultExp.totalAssets() == 2.5e8

    # Test pricePerShare to equal 1
    assert setup.wrapper.pricePerShare() == 1e8
    print("-- 2nd Withdraw --")
    print("Wrapper's PPS:", setup.wrapper.pricePerShare())
    print("Vault's PPS:", setup.vaultExp.pricePerShare())

    # User attempts to withdraw more assets than the available on the vaultExp and reverts
    with brownie.reverts():
        setup.wrapper.withdraw(16e8, {"from": randomUser2})

    # === Disable experimental mode === #

    setup.wrapper.disableExperimentalMode({"from": deployer})

    chain.sleep(10000)
    chain.mine(1)

    # bestVault should be the registry's latest vault
    assert setup.wrapper.bestVault() == setup.vault.address
    assert setup.wrapper.allVaults() == [setup.vault.address]
    assert setup.vault.totalAssets() == 0

    # User attempts to withdraw their 2.5 tokens left on experimental vault but this
    setup.wrapper.balanceOf(randomUser2.address) == 2.5e8
    setup.wbtc.balanceOf(randomUser2.address) == 17.5e8
    setup.wrapper.withdraw(2.5e8, {"from": randomUser2})
    setup.wbtc.balanceOf(randomUser2.address) == 17.5e8
    setup.wrapper.balanceOf(randomUser2.address) == 0

    # Deposit 5 tokens from User 2 to wrapper
    setup.wrapper.deposit(5e8, [], {"from": randomUser2})
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 5e8
    assert setup.vault.totalAssets() == 5e8
    assert setup.vaultExp.totalAssets() == 2.5e8


@pytest.mark.skip()
def test_gustlist_authentication(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    distributor = setup.namedAccounts["distributor"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # Set total deposit cap
    setup.guestlist.setTotalDepositCap(20e8)

    # Set merkle proof verification from Gueslist
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
        setup.wbtc.transfer(user, 1e8, {"from": distributor})

        # Approve wrapper to transfer user's token
        setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": user})

        # User deposits 1 token through wrapper
        assert setup.wrapper.totalWrapperBalance(user) == 0
        setup.wrapper.deposit(1e8, proof, {"from": user})

        assert abs(setup.wrapper.totalWrapperBalance(user) - 1e8) <= TOLERANCE

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
        setup.wbtc.transfer(user, 1e8, {"from": distributor})

        # Approve wrapper to transfer user's token
        setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": user})

        tx = setup.guestlist.proveInvitation(user, proof)
        assert tx.events[0]["guestRoot"] == merkleRoot
        assert tx.events[0]["account"] == user

        # User deposits 1 token through wrapper (without proof)
        assert setup.wrapper.totalWrapperBalance(user) == 0
        setup.wrapper.deposit(1e8, [], {"from": user})

        assert abs(setup.wrapper.totalWrapperBalance(user) - 1e8) <= TOLERANCE

    # Test depositing with user on Gueslist but with no merkle proof

    setup.wrapper.deposit(1e8, [], {"from": randomUser1})
    assert (
        abs(setup.wrapper.totalWrapperBalance(randomUser1.address) - 1e8) <= TOLERANCE
    )

    # Test manually removing guest (with no proof) from guestlist and attempting to deposit

    # Remove user from guestlist
    setup.guestlist.setGuests([randomUser1.address], [False])

    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(1e8, [], {"from": randomUser1})

    # Test depositing with user not on Gueslist and with no merkle proof

    # Approve wrapper to transfer user's token
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser3})

    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(1e8, [], {"from": randomUser3})
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # At this stage there are 7 wbtc deposited and the Wrapper's cap is 20

    # Total wrapper limit remaining
    assert abs(setup.guestlist.remainingTotalDepositAllowed() - 13e8) <= TOLERANCE
    # Individual limit for randomUser2 remaining
    assert setup.guestlist.remainingUserDepositAllowed(randomUser2.address) == 15e8

    # User attempts to deposit 14 wbtc for a total of 21 wbtc and it reverts
    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(14e8, [], {"from": randomUser2})

    # User attempts to deposit the remaining total deposit allowed + 1 and it reverts
    with brownie.reverts("guest-list-authorization"):
        setup.wrapper.deposit(
            setup.guestlist.remainingTotalDepositAllowed() + 1,
            [],
            {"from": randomUser2},
        )

    # User deposits the remaining total deposit allowed and it goes through
    setup.wrapper.deposit(
        setup.guestlist.remainingTotalDepositAllowed(), [], {"from": randomUser2}
    )


@pytest.mark.skip()
def test_initial_deposit_conditions(setup):
    randomUser1 = setup.namedAccounts["randomUser1"]
    randomUser2 = setup.namedAccounts["randomUser2"]
    randomUser3 = setup.namedAccounts["randomUser3"]
    deployer = setup.namedAccounts["deployer"]

    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 100e8, {"from": randomUser1})

    # Remove merkle proof verification from Gueslist
    setup.guestlist.setGuestRoot("0x0")

    # Link guestlist to wrapper
    setup.wrapper.setGuestList(setup.guestlist.address, {"from": deployer})

    # Disable experimental mode
    setup.wrapper.disableExperimentalMode({"from": deployer})

    # Set max deviation threshold
    setup.wrapper.setWithdrawalMaxDeviationThreshold(DEVIATION_MAX)

    # User deposits to vault through wrapper
    setup.wrapper.deposit(5e8, [], {"from": randomUser2})

    # Deploying new version of vault
    vaultPPS = deployer.deploy(YearnTokenVault_PPS)
    vaultPPS.initialize(
        setup.wbtc.address, deployer.address, AddressZero, "YearnWBTCV2", "vyWBTCV2"
    )
    vaultPPS.setDepositLimit(24e8)
    # Set a PPS > 1 for the underlying vault
    vaultPPS.setPricePerShare(2e8)

    assert vaultPPS.pricePerShare() == 2e8

    # Add vault to registry
    setup.yearnRegistry.newRelease(vaultPPS.address)
    setup.yearnRegistry.endorseVault(vaultPPS.address)

    # Check that vaultPPS is current 'bestVault'
    assert setup.wrapper.bestVault() == vaultPPS.address

    # User 2 deposits another 5 tokens into new vault should revert because PPS > 1
    with brownie.reverts():
        setup.wrapper.deposit(5e8, [], {"from": randomUser2})
