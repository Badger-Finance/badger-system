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

TOLERANCE = 71

@pytest.fixture(scope="module", autouse=True)
def setup(SimpleWrapperGatedUpgradeable, YearnRegistry, VipCappedGuestListWrapperUpgradeable):

    # Assign accounts
    manager = accounts[2]
    guardian = accounts[3]
    randomUser1 = accounts[4]
    randomUser2 = accounts[5]
    randomUser3 = accounts[6]
    whale = accounts[7]

    # WBTC owner account
    wbtcOwner = accounts.at('0xca06411bd7a7296d7dbdd0050dfc846e95febeb7', force=True)

    # byvWBTC owner/affiliate account (devMultisig)
    affiliate = accounts.at('0xB65cef03b9B89f99517643226d76e286ee999e77', force=True)

    namedAccounts = {
        "affiliate": affiliate, 
        "manager": manager, 
        "guardian": guardian,
        "randomUser1": randomUser1,
        "randomUser2": randomUser2,
        "randomUser3": randomUser3,
        "whale": whale,
        "wbtcOwner": wbtcOwner,
    }

    # WBTC
    abi = artifacts.wbtc["wbtc"]["abi"]
    wbtc = Contract.from_abi('WBTC', registry.tokens.wbtc, abi, wbtcOwner)
    print(wbtc.name() + ' fetched')

    assert wbtc.owner() == wbtcOwner.address

    # affiliate mints WBTC tokens for users
    wbtc.mint(randomUser1.address, 10e8)
    wbtc.mint(randomUser2.address, 20e8)
    wbtc.mint(randomUser3.address, 10e8)
    wbtc.mint(whale.address, 1000e8)

    assert wbtc.balanceOf(randomUser1.address) == 10e8
    assert wbtc.balanceOf(randomUser2.address) == 20e8
    assert wbtc.balanceOf(randomUser3.address) == 10e8
    assert wbtc.balanceOf(whale.address) == 1000e8

    # Badger WBTC yVault (byvWBTC)
    abi = artifacts.byvwbtc["byvwbtc"]["abi"]
    wrapper = Contract.from_abi('SimpleWrapperGatedUpgradable', '0x4b92d19c11435614CD49Af1b589001b7c08cD4D5', abi, affiliate)

    assert wrapper.affiliate() == affiliate.address

    # Badger WBTC yVault (byvWBTC)
    abi = artifacts.guestlist["guestlist"]["abi"]
    guestlist = Contract.from_abi('VipCappedGuestListWrapperUpgradable', '0x19a0420b98F9a34B2b9Db3BcBA35a6fFfeBB7aDd', abi, affiliate)

    assert guestlist.owner() == affiliate.address

    assert guestlist.totalDepositCap() == 170e8
    assert guestlist.userDepositCap() == 4e8
    assert guestlist.guestRoot() != '0x00'

    yield namedtuple(
        'setup', 
        'wbtc wrapper guestlist namedAccounts'
    )(
        wbtc, 
        wrapper,
        guestlist, 
        namedAccounts
    )

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

#@pytest.mark.skip()
def test_open_deposit_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts['randomUser1']
    randomUser2 = setup.namedAccounts['randomUser2']
    randomUser3 = setup.namedAccounts['randomUser3']
    whale = setup.namedAccounts['whale']
    affiliate = setup.namedAccounts['affiliate']

    # === Open Vault ===#

    # Remove user deposit cap (Set cap to BTC max supply)
    setup.guestlist.setUserDepositCap(21e14)
    assert setup.guestlist.userDepositCap() == 21e14

    # Remove total deposit cap (Set cap to BTC max supply)
    setup.guestlist.setTotalDepositCap(21e14)
    assert setup.guestlist.totalDepositCap() == 21e14

    # Remove merkleRoot for guestlist - Guestlist removed
    setup.guestlist.setGuestRoot('0x00')
    assert setup.guestlist.guestRoot() == '0x00'

    # Get current withdrawalFee i.e. 50 -> 0.5% -> 0.005
    fee = setup.wrapper.withdrawalFee()/10000
        
    # === Deposit flow === #
    
    # Approve wrapper as spender of wbtc for users
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": randomUser3})
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": randomUser1})
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": whale}) # Whale

    # = User 2: Has 20 wbtc, deposits 1, not on Guestlist = #
    # Random user (not from guestlist) deposits 1 Token
    setup.wrapper.deposit(1e8, [], {"from": randomUser2})
    print("-- 1st User Deposits 1 --")
    assert setup.wbtc.balanceOf(randomUser2.address) == 19e8

    # Check balance of user within wrapper is within tolerance
    assert abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 1e8) < TOLERANCE

    # deposit/pps of wrapper shares are minted for depositor
    assert abs(setup.wrapper.balanceOf(randomUser2.address) - (1e8/setup.wrapper.pricePerShare())*1e8) < TOLERANCE

    # Remaining deposit allowed for User 2: 21e14 - 1e8
    assert abs(abs(setup.guestlist.remainingUserDepositAllowed(randomUser2.address) - 21e14) - 1e8) < TOLERANCE

    chain.sleep(86400)
    chain.mine(1)

    # = User 1: Has 10 wbtc, deposits 10, not on Guestlist = #
    # Another random user (not from guestlist) deposits all their Tokens (10)
    setup.wrapper.deposit([], {"from": randomUser1})
    print("-- 2nd User Deposits 10 --")
    assert setup.wbtc.balanceOf(randomUser1.address) == 0

    # Check balance of user within wrapper is within tolerance
    assert abs(setup.wrapper.totalWrapperBalance(randomUser1.address) - 10e8) <= TOLERANCE

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert abs(setup.wrapper.balanceOf(randomUser1.address) - (10e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE

    # Remaining deposit allowed for User 2: 21e14 - 10e8
    assert abs(abs(setup.guestlist.remainingUserDepositAllowed(randomUser1.address) - 21e14) - 10e8) <= TOLERANCE

    chain.sleep(86400)
    chain.mine(1)

    # = User 3: Has 10 wbtc, deposits 1, not on Guestlist = #
    # Random user (not from guestlist) attempts to deposit 1 token
    # Should not revert since root is set to 0x0
    setup.wrapper.deposit(1e8, [], {"from": randomUser3})
    print("-- 3rd User Deposits 1 --")
    assert setup.wbtc.balanceOf(randomUser3.address) == 9e8

    # Check balance of user within wrapper is within tolerance
    assert abs(setup.wrapper.totalWrapperBalance(randomUser3.address) - 1e8) <= TOLERANCE

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert abs(setup.wrapper.balanceOf(randomUser3.address) - (1e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE

    # Remaining deposit allowed for User 2: 21e14 - 1e8
    assert abs(abs(setup.guestlist.remainingUserDepositAllowed(randomUser3.address) - 21e14) - 1e8) <= TOLERANCE

    # = User 1: Has 0 wbtc, deposits 1 and then all, not on Guestlist = #
    # Random user (from guestlist) attempts to deposit 1 and then all tokens
    # Should revert since user has no tokens
    assert setup.wbtc.balanceOf(randomUser1.address) == 0
    with brownie.reverts():
        setup.wrapper.deposit(1e8, [], {"from": randomUser1})
    with brownie.reverts():
        setup.wrapper.deposit([], {"from": randomUser1})
    # User's bvyWBTC balance remains the same 
    assert abs(setup.wrapper.balanceOf(randomUser1.address) - (10e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE

    chain.sleep(86400)
    chain.mine(1)

    # = Whale: Has 100 wbtc, deposits 1000, not on Guestlist = #
    assert setup.wbtc.balanceOf(whale.address) == 1000e8

    setup.wrapper.deposit([], {"from": whale})
    print("-- Whale Deposits 1000 --")
    assert setup.wbtc.balanceOf(whale.address) == 0

    # Check balance of user within wrapper is within tolerance
    assert abs(setup.wrapper.totalWrapperBalance(whale.address) - 1000e8) <= TOLERANCE

    # deposit/pps of wrapper shares are minted for depositor and vault shares are 0 for depositor
    assert abs(setup.wrapper.balanceOf(whale.address) - (1000e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE

    # Remaining deposit allowed for User 2: 21e14 - 10e8
    assert abs(abs(setup.guestlist.remainingUserDepositAllowed(whale.address) - 21e14) - 1000e8) <= TOLERANCE

    chain.sleep(86400)
    chain.mine(1)


    # === Withdraw flow === #

    # = User 2: Has 19 wbtc, withdraws half their shares = #
    assert setup.wbtc.balanceOf(randomUser2.address) == 19e8
    shares = setup.wrapper.balanceOf(randomUser2.address)/2

    setup.wrapper.withdraw(shares, {"from": randomUser2})
    print('-- 1st User withdraws ' + str(shares) + ' shares --')
    print('Withdrew ' + str(abs(19e8 - setup.wbtc.balanceOf(randomUser2.address))/1e8) + ' wbtc')
    assert abs(setup.wbtc.balanceOf(randomUser2.address) - 19.5e8)-0.5e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser2.address) <= 19.5e8

    # Check balance of user within wrapper
    assert abs(setup.wrapper.totalWrapperBalance(randomUser2.address) - 0.5e8) <= TOLERANCE

    # wrapper shares are burned for withdrawer and yvwbtc shares are still 0 for withdrawer
    assert abs(setup.wrapper.balanceOf(randomUser2.address) - (0.5e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE

    chain.sleep(86400)
    chain.mine(1)

    # = User 1: Has 0 Tokens, withdraws all = #
    assert setup.wbtc.balanceOf(randomUser1.address) == 0
    shares = setup.wrapper.balanceOf(randomUser1.address) 

    setup.wrapper.withdraw({"from": randomUser1})
    print('-- 2nd User withdraws ' + str(shares) + ' shares --')
    print('Withdrew ' + str(setup.wbtc.balanceOf(randomUser1.address)/1e8) + ' wbtc')
    assert abs(setup.wbtc.balanceOf(randomUser1.address) - 10e8)-10e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser1.address) <= 10e8

    # Check balance of user within wrapper
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0

    # wrapper shares are burned for withdrawer and yvwbtc shares are still 0 for withdrawer
    assert setup.wrapper.balanceOf(randomUser1.address) == 0

    chain.sleep(86400)
    chain.mine(1)

    # = User 3: Has 9 wbtc, withdraws all = #
    assert setup.wbtc.balanceOf(randomUser3.address) == 9e8
    shares = setup.wrapper.balanceOf(randomUser3.address) 

    setup.wrapper.withdraw({"from": randomUser3})
    print('-- 3rd User withdraws ' + str(shares) + ' shares --')    
    print('Withdrew ' + str(abs(9e8 - setup.wbtc.balanceOf(randomUser3.address))) + ' wbtc')
    assert abs(setup.wbtc.balanceOf(randomUser3.address) - 10e8)-1e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10e8

    # = User 3: Has 10 wbtc, withdraws 1 share= #
    # Random user attempts to withdraw 1 share
    # Should revert since user has no tokens on yvwbtc
    with brownie.reverts():
        setup.wrapper.withdraw(1e8, {"from": randomUser3})
    # User's token balance remains the same 
    assert abs(setup.wbtc.balanceOf(randomUser3.address) - 10e8)-1e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10e8

    chain.sleep(86400)
    chain.mine(1)

    # = User 2 sends remaining half of shares to user 3 for withdrawal = #
    shares = setup.wrapper.balanceOf(randomUser2.address)
    print('-- 2nd User transfers ' + str(shares) + ' shares to 3rd User --')
    setup.wrapper.transfer(randomUser3.address, shares, {"from": randomUser2})

    assert setup.wrapper.balanceOf(randomUser3.address) == shares

    # User 3 withdraws using the shares received from user 2, equivalent to 0.5
    setup.wrapper.withdraw(shares, {"from": randomUser3})
    print('-- 3rd User withdraws ' + str(shares) + ' shares --')
    print('Withdrew ' + str(abs(10e8 - setup.wbtc.balanceOf(randomUser3.address))) + ' wbtc')
    # wbtc balance of user 3: 10 + 0.5 = ~10.5 (fees on total withdrew -> 1.5 wBTC)
    assert abs(setup.wbtc.balanceOf(randomUser3.address) - 10.5e8)-1.5e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 10.5e8

    # = Whale: Has 0 Tokens, withdraws all = #
    assert setup.wbtc.balanceOf(whale.address) == 0
    shares = setup.wrapper.balanceOf(whale.address) 

    setup.wrapper.withdraw({"from": whale})
    print('-- Whale withdraws ' + str(shares) + ' shares --')
    print('Withdrew ' + str(setup.wbtc.balanceOf(whale.address)) + ' wbtc')
    assert abs(setup.wbtc.balanceOf(whale.address) - 1000e8)-1000e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(whale.address) <= 1000e8
    print('totalWrapperBalance(whale)', setup.wrapper.totalWrapperBalance(whale.address))
    print('shareValue(whale)', setup.wrapper.shareValue(setup.wrapper.totalWrapperBalance(whale.address)))

    # Check balance of user within wrapper
    assert setup.wrapper.totalWrapperBalance(whale.address) == 0

    # = Existing user withdraws their wBTC (0x43f44Ad26a18777F500Fb7496D1aF795cc1d3543) = #
    # 2.38109117 wBTC -> 2.3695172 byvWBTC
    holder = accounts.at('0x43f44Ad26a18777F500Fb7496D1aF795cc1d3543', force=True)

    assert setup.wbtc.balanceOf(holder.address) == 0
    shares = setup.wrapper.balanceOf(holder.address) 
    assert shares == 2.3695172e8

    setup.wrapper.withdraw({"from": holder})
    print('-- Holder withdraws ' + str(shares) + ' shares --')
    print('Withdrew ' + str(setup.wbtc.balanceOf(holder.address)) + ' wbtc')
    assert abs(setup.wbtc.balanceOf(holder.address) - 2.38109117e8)-2.3695172e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(holder.address) <= 2.38109117e8


    assert setup.wrapper.balanceOf(randomUser1.address) == 0
    assert setup.wrapper.balanceOf(randomUser2.address) == 0 
    assert setup.wrapper.balanceOf(randomUser3.address) == 0
    assert setup.wrapper.balanceOf(whale.address) == 0
    assert setup.wrapper.balanceOf(holder.address) == 0

    print('User1 final WBTC:', setup.wbtc.balanceOf(randomUser1.address))
    print('User2 final WBTC:', setup.wbtc.balanceOf(randomUser2.address))
    print('User3 final WBTC:', setup.wbtc.balanceOf(randomUser3.address))
    print('Whale final WBTC:', setup.wbtc.balanceOf(whale.address))
    print('Holder final WBTC:', setup.wbtc.balanceOf(holder.address))
 
#@pytest.mark.skip()
def test_depositFor_withdraw_flow(setup):
    randomUser1 = setup.namedAccounts['randomUser1']
    randomUser2 = setup.namedAccounts['randomUser2']
    randomUser3 = setup.namedAccounts['randomUser3']
    affiliate = setup.namedAccounts['affiliate']


    # === Open Vault ===#

    # Remove user deposit cap (Set cap to BTC max supply)
    setup.guestlist.setUserDepositCap(21e14)
    assert setup.guestlist.userDepositCap() == 21e14

    # Remove total deposit cap (Set cap to BTC max supply)
    setup.guestlist.setTotalDepositCap(21e14)
    assert setup.guestlist.totalDepositCap() == 21e14

    # Remove merkleRoot for guestlist - Guestlist removed
    setup.guestlist.setGuestRoot('0x00')
    assert setup.guestlist.guestRoot() == '0x00'

    # Get current withdrawalFee i.e. 50 -> 0.5% -> 0.005
    fee = setup.wrapper.withdrawalFee()/10000



    # Approve wrapper as spender of wbtc for users
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": randomUser2})
    setup.wbtc.approve(setup.wrapper.address, 21e14, {"from": randomUser3})

    # total wrapper balance of User 1, 2, 3  = 0
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # === Deposit flow === #

    # User 2 (not on guestlist) deposits on behalf of User 1 (on guestlist)
    setup.wrapper.depositFor(randomUser1.address, 1e8, [], {'from': randomUser2})

    # total wrapper balance of User 1 = 1 and User 2 = 2
    assert abs(setup.wrapper.totalWrapperBalance(randomUser1.address) - 1e8) <= TOLERANCE
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert abs(setup.wrapper.balanceOf(randomUser1.address) - (1e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # User 2 (not on guestlist) deposits on behalf of User 3 (not on guestlist)
    setup.wrapper.depositFor(randomUser3.address, 1e8, [], {'from': randomUser2})

    # total wrapper balance of User 1 = 0 and User 2 = 1
    assert abs(setup.wrapper.totalWrapperBalance(randomUser3.address) - 1e8) <= TOLERANCE
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0

    # Wrapper shares are created only for receipient (User 1)
    assert abs(setup.wrapper.balanceOf(randomUser3.address) - (1e8/setup.wrapper.pricePerShare())*1e8) <= TOLERANCE
    assert setup.wrapper.balanceOf(randomUser2.address) == 0

    # === Withdraw flow === #

    # Reverts when User 2 tries to withdraw
    with brownie.reverts():
        setup.wrapper.withdraw(0.1e8, {"from": randomUser2})

    # User 1 withdraws using their received shares
    setup.wrapper.withdraw({'from': randomUser1})
    # User 1 gets 1 wbtc in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser1.address) == 0
    assert abs(setup.wbtc.balanceOf(randomUser1.address) - 11e8)-1e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser1.address) <= 11e8

    # User 3 withdraws using their received shares
    setup.wrapper.withdraw({'from': randomUser3})
    # User 3 gets 1 wbtc in return (10 + 1 = 11)
    assert setup.wrapper.balanceOf(randomUser3.address) == 0
    assert abs(setup.wbtc.balanceOf(randomUser3.address) - 11e8)-1e8*fee <= TOLERANCE
    assert setup.wbtc.balanceOf(randomUser3.address) <= 11e8

    # Wrapper balance of all users is zero
    assert setup.wrapper.totalWrapperBalance(randomUser1.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser2.address) == 0
    assert setup.wrapper.totalWrapperBalance(randomUser3.address) == 0

    # wbtc balance of User 2 is 18 (20 - 2 = 18)
    assert setup.wbtc.balanceOf(randomUser2.address) == 18e8

