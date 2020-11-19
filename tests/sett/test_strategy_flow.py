from tests.sett.strategy_test_config import confirm_deposit, confirm_earn, confirm_withdraw
from tests.conftest import distribute_rewards_escrow
from helpers.time_utils import daysToSeconds
import brownie
from helpers.proxy_utils import deploy_proxy
import pytest
from operator import itemgetter
from brownie.test import given, strategy
from brownie import *
from helpers.constants import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from dotmap import DotMap
from scripts.deploy.deploy_badger import main
from helpers.registry import whale_registry

"""
E2E isolated tests for StrategyBadgerRewards
This strategy stakes it's assets in the special rewards pool, increasing it's badger position.
"""

def distribute_from_whales(badger, recipient):
    print (len(whale_registry.items()))
    for key, whale in whale_registry.items():
        print(whale.token)
        if whale.token:
            token = interface.IERC20(whale.token)
            token.transfer(recipient, token.balanceOf(whale.whale), {"from": whale.whale})

def sett_snapshot(sett, strategy, account):
    want = interface.IERC20(strategy.want())

    return DotMap(
        want=DotMap(
            userBalance=want.balanceOf(account)
        ),
        sett=DotMap(
            totalSupply=sett.totalSupply(),
            userBalance=sett.balanceOf(account),
            wantReserve=want.balanceOf(sett),
            available=sett.available(),
            balance=sett.balance(),
            # pricePerFullShare=sett.getPricePerFullShare()
        ),
        strategy=DotMap(
            balanceOf=strategy.balanceOf(),
            balanceOfWant=strategy.balanceOfWant(),
            balanceOfPool=strategy.balanceOfPool(),
            performanceFeeGovernance=strategy.performanceFeeGovernance(),
            performanceFeeStrategist=strategy.performanceFeeStrategist(),
            withdrawalFee=strategy.withdrawalFee(),
        )
    )

# def get_strategy_pool_balance(strategy):
#     strategyName = strategy.getName()

#     if strategyName == "StrategyCurveGauge":
#     if strategyName == "StrategyPickleMetaFarm":
#     if strategyName == "StrategyHarvestMetaFarm":
#     if strategyName == "StrategyBadgerLpMetaFarm":
#     if strategyName == "StrategyBadgerRewards":

def get_sett_by_id(badger, id):
    contracts=DotMap()

    if id == 'native.renCrv':
        contracts.sett = badger.sett.native.renCrv
        contracts.strategy = badger.sett.native.strategies.renCrv
    if id == 'native.badger':
        contracts.sett = badger.sett.native.badger
        contracts.strategy = badger.sett.native.strategies.badger
    if id == 'native.sbtcCrv':
        contracts.sett = badger.sett.native.sbtcCrv
        contracts.strategy = badger.sett.native.strategies.sbtcCrv
    if id == 'native.tbtcCrv':
        contracts.sett = badger.sett.native.tbtcCrv
        contracts.strategy = badger.sett.native.strategies.tbtcCrv
    if id == 'harvest.renCrv':
        contracts.sett = badger.sett.harvest.renCrv
        contracts.strategy = badger.sett.harvest.strategies.renCrv
    if id == 'pickle.renCrv':
        contracts.sett = badger.sett.pickle.renCrv
        contracts.strategy = badger.sett.pickle.strategies.renCrv

    contracts.controller = interface.IController(contracts.sett.controller())
    contracts.want = interface.IERC20(contracts.strategy.want())

    return contracts

@pytest.fixture()
def shared_setup(badger):
    distribute_rewards_escrow(badger, badger.token, badger.deployer, Wei("100000 ether"))
    distribute_from_whales(badger, badger.deployer)
    return badger

@pytest.mark.parametrize('settId', ['native.renCrv', 'native.badger', 'native.sbtcCrv', 'native.tbtcCrv'])
# @pytest.mark.parametrize('settId', ['pickle.renCrv'])
def test_deposit_withdraw_single_user(shared_setup, settId):
    badger = shared_setup
    settConfig = get_sett_by_id(badger, settId)

    controller = settConfig.controller
    sett = settConfig.sett
    strategy = settConfig.strategy
    want = settConfig.want

    deployer = badger.deployer
    randomUser = accounts[6]

    # Deposit
    
    depositAmount = Wei("1 ether")
    assert want.balanceOf(deployer) >= depositAmount
    want.approve(sett, MaxUint256, {'from': deployer})

    before = sett_snapshot(sett, strategy, deployer)
    sett.deposit(depositAmount, {'from': deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_deposit(before, after, deployer, depositAmount)

    # Earn
    with brownie.reverts("onlyAuthorizedActors"):
        sett.earn({'from': randomUser})

    min = sett.min()
    max = sett.max()
    remain = max - min

    assert sett.keeper() == deployer

    before = sett_snapshot(sett, strategy, deployer)
    sett.earn({'from': deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_earn(before, after)

    chain.sleep(15)
    chain.mine(1)

    before = sett_snapshot(sett, strategy, deployer)
    sett.withdraw(depositAmount // 2, {'from': deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_withdraw(before, after, deployer)

    chain.sleep(15)
    chain.mine(1)

    before = sett_snapshot(sett, strategy, deployer)
    sett.withdrawAll({'from': deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_withdraw(before, after, deployer)

@pytest.mark.skip(reason="no way of currently testing this")
def single_user_harvest_flow(shared_setup):
    """
    After each action, run the usual checks.

    --Setup--
    User deposits into Sett
    Deposit into Strat via earn()

    Wait some time and tend()
    - Expect call to return the tendable amount properly
    - Expect pickle balance in PickleJar to increase
    - Confirm Tend() event with real values
    - Expect no Pickle idle in Strat

    Wait some time and tend()
    - Expect call to return the tendable amount properly
    - Expect pickle balance in PickleJar to increase
    - Confirm Tend() event with real values
    - Expect no Pickle idle in Strat

    Wait some time and harvest()
    - Expect no Pickle staked in PickleStaking
    - Expect no Pickle staked in PickleChef
    - Expect underlying position to increase (represented by pTokens)

    Wait some time and tend()
    Wait some time and harvest()

    User withdraws very small amount that is covered by Sett reserves

    User withdraws partially

    Wait some time and tend()

    User withdraws remainder
        - Price per full share should NOT have inceased as we never realized gains

    """
    badger = shared_setup
    controller = badger.sett.native.controller
    sett = badger.sett.native.badger
    strategy = badger.sett.native.strategies.badger
    deployer = badger.deployer
    randomUser = accounts[6]
    tendable = strategy.isTendable()

    before = sett_snapshot(sett, strategy, deployer)
    depositAmount = Wei("1 ether")
    sett.deposit(depositAmount, {'from': deployer})
    after = sett_snapshot(sett, strategy, deployer)
    confirm_deposit(before, after, deployer, depositAmount)
    
    before_harvest = sett_snapshot(sett, strategy, deployer)

    if (tendable):
        with brownie.reverts('onlyAuthorizedActors'):
            strategy.tend({'from': randomUser})
        strategy.tend({'from': deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    if (tendable):
        strategy.tend({'from': deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    with brownie.reverts('onlyAuthorizedActors'):
        strategy.harvest({'from': randomUser})
    strategy.harvest({'from': deployer})

    after_harvest = sett_snapshot(sett, strategy, deployer)

    assert after_harvest.sett.pricePerFullShare > before_harvest.sett.pricePerFullShare
    assert after_harvest.strategy.balanceOf > before_harvest.strategy.balanceOf

    chain.sleep(daysToSeconds(1))
    chain.mine()

    if (tendable):
        strategy.tend({'from': deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    before_harvest = sett_snapshot(sett, strategy, deployer)
    strategy.harvest({'from': deployer})
    after_harvest = sett_snapshot(sett, strategy, deployer)

    assert after_harvest.sett.pricePerFullShare > before_harvest.sett.pricePerFullShare
    assert after_harvest.strategy.balanceOf > before_harvest.strategy.balanceOf

@pytest.mark.skip(reason="no way of currently testing this")
def test_harvest_single_user(shared_setup):
    badger = shared_setup
    controller = badger.sett.native.controller
    sett = badger.sett.native.badger
    strategy = badger.sett.native.strategies.badger
    deployer = badger.deployer
    randomUser = accounts[6]

    depositAmount = Wei("1 ether")

    single_user_harvest_flow(badger)

    sett.withdraw(depositAmount // 2, {'from': deployer})
    sett.withdrawAll({'from': deployer})

@pytest.mark.skip(reason="no way of currently testing this")
def test_migrate_single_user(shared_setup):
    badger = shared_setup
    controller = badger.sett.native.controller
    sett = badger.sett.native.badger
    strategy = badger.sett.native.strategies.badger
    deployer = badger.deployer
    randomUser = accounts[6]
    """
    --Setup--
    User deposits into Sett
    Deposit into Strat via earn()
    tend()
    harvest()

    withdrawAll
        - Ensure only appropriate parties can call (roll back between each call)
    """
    controller = badger.sett.native.controller
    sett = badger.sett.native.badger
    strategy = badger.sett.native.strategies.badger
    deployer = badger.deployer
    randomUser = accounts[6]

    single_user_harvest_flow(badger)
    with brownie.reverts():
        controller.withdrawAll(strategy.want(), {'from': randomUser})
        
    controller.withdrawAll(strategy.want(), {'from': deployer})

@pytest.mark.skip(reason="no way of currently testing this")
def test_action_flow(badger):
    assert True
    # # TODO: Get token randomly from selection
    # sett = badger.sett.native.badger
    # controller = Controller.at(sett.controller())
    # strategy = controller.getStrategy(sett.token())
    # want = strategy.want()

    # assert sett.token() == strategy.want()
    
    # users = [badger.deployer, accounts[2], accounts[3], accounts[4]]
    # distribute_test_asset(badger, users)
    # approve_assets(badger, users)

    # rounds = 100

    # user = get_random_user(users)

    # # Initial deposit
    # user = get_random_user(users)
    # amount = get_random_amount(want, user)
    # sett.deposit(amount, {'from': user})

    # for round in range(rounds):
    #     # Take user action
    #     take_keeper_action(badger, sett, strategy, user)

    #     user = get_random_user(users)
    #     take_user_action(badger, sett, strategy, user)

    #     take_keeper_action(badger, sett, strategy, user)


