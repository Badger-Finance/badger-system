from tests.test_recorder import TestRecorder
from tests.sett.helpers.snapshots import (
    confirm_deposit,
    confirm_earn,
    confirm_harvest,
    confirm_tend,
    confirm_withdraw,
    sett_snapshot,
)
from tests.conftest import (
    badger_single_sett, distribute_from_whales,
    distribute_rewards_escrow,
    get_sett_by_id,
)
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


@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "pickle.renCrv",
        "harvest.renCrv",
    ],
)
def test_strategy_permissions(settId):
    suiteName = "test_single_user_harvest_flow" + ": " + settId
    testRecorder = TestRecorder(suiteName)

    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    randomUser = accounts[6]
    
    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)
    depositAmount = Wei("1 ether")
    assert startingBalance >= depositAmount
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    chain.sleep(daysToSeconds(2))
    chain.mine()

    # ===== Strategy =====
    # initialized = true

    # deposit: _onlyAuthorizedActorsOrController
    with brownie.reverts("_onlyAuthorizedActors"):
        strategy.deposit({"from": randomUser})
    
    authorizedActors = [
        strategy.governance(),
        strategy.strategist(),
        strategy.keeper(),
        controller
    ]

    accounts.at(strategy.governance(), force=True)
    accounts.at(strategy.strategist(), force=True)
    accounts.at(strategy.keeper(), force=True)
    accounts.at(controller, force=True)

    with brownie.reverts("_onlyAuthorizedActors"):
        strategy.deposit({"from": randomUser})

    for actor in authorizedActors:
        chain.snapshot()
        strategy.deposit({"from": actor})
        chain.revert()
        
    # harvest: _onlyAuthorizedActors
    with brownie.reverts("_onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    for actor in authorizedActors:
        chain.snapshot()
        strategy.harvest({"from": actor})
        chain.revert()

    # (if tendable) tend: _onlyAuthorizedActors
    if tendable:
        with brownie.reverts("_onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        for actor in authorizedActors:
            chain.snapshot()
            strategy.tend({"from": actor})
            chain.revert()

    actorsToCheck = [
        randomUser,
        strategy.governance(),
        strategy.strategist(),
        strategy.keeper(),
    ]

    # withdrawAll _onlyController
    for actor in actorsToCheck:
        with brownie.reverts("_onlyController"):
            strategy.withdrawAll({"from": actor})

    chain.snapshot()
    strategy.withdrawAll({"from": controller})
    chain.revert()

    # withdraw _onlyController
    for actor in actorsToCheck:
        with brownie.reverts("_onlyController"):
            strategy.withdraw(1, {"from": actor})

    chain.snapshot()
    strategy.withdraw(1, {"from": controller})
    chain.revert()

    # withdrawOther _onlyNotProtectedTokens
    for actor in actorsToCheck:
        with brownie.reverts("_onlyController"):
            strategy.withdrawOther(controller, {"from": actor})

    chain.snapshot()
    strategy.withdrawOther(controller, {"from": controller})
    chain.revert()
    
    authorizedPausers = [
        strategy.governance(),
        strategy.strategist(),
        strategy.guardian()
    ]
    # pause _onlyAuthorizedPausers
    
    # unpause _onlyAuthorizedPausers

    # Pause Gated Functions
    # deposit
    # withdraw
    # withdrawAll
    # withdrawOther
    # harvest
    # tend

    # Unpause should unlock
    # deposit
    # withdraw
    # withdrawAll
    # withdrawOther
    # harvest
    # tend

    # Governance params: _onlyGovernance
    #setGuardian
    #setWithdrawalFee
    #setPerformanceFeeStrategist
    #setPerformanceFeeGovernance
    #setController

    # Special fees: _onlyGovernance
    # Pickle:
    # Pickle:
    

    # Harvest:
    # Harvest:
    assert False

@pytest.skip()
def test_sett_permissions(sett_pickle_meta_farm: BadgerSystem):
    # ===== Sett =====
    # initialize - no-one
    # initialized = true
    
    # == All Valid Users ==
    # EOAs or approved contracts, can only take one action per block

    # deposit
    # depositAll
    # withdraw
    # withdrawAll

    # == Governance ==
    # setMin
    # setController

    # == Controller ==
    # harvest

    # == Authorized Actors ==
    # earn

    assert False

@pytest.skip()
def test_controller_permissions(sett_pickle_meta_farm: BadgerSystem):
    # ===== Controller =====
    # initialize - no-one
    # initialized = true
    # earn _onlyApprovedForWant
    # withdraw (only current vault for underlying)

    # == Governance or Strategist ==
    # harvestExtraRewards _onlyGovernanceOrStrategist
    # inCaseTokensGetStuck _onlyGovernanceOrStrategist
    # inCaseStrategyTokenGetStuck _onlyGovernanceOrStrategist
    # setConverter _onlyGovernanceOrStrategist
    # setStrategy _onlyGovernanceOrStrategist
    # setVault _onlyGovernanceOrStrategist

    # == Governance Only ==
    # approveStrategy _onlyGovernance
    # revokeStrategy _onlyGovernance
    # setRewards _onlyGovernance
    # setSplit _onlyGovernance
    # etOneSplit _onlyGovernance
    assert False
    