from tests.test_recorder import TestRecorder
from tests.conftest import (
    badger_single_sett,
)
from helpers.time_utils import daysToSeconds
import brownie
import pytest
from brownie import *
from helpers.constants import *
from dotmap import DotMap


@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_strategy_permissions(settId):
    suiteName = "test_strategy_permissions" + ": " + settId
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

    chain.sleep(daysToSeconds(1))
    chain.mine()

    sett.earn({"from": deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    strategy.harvest({"from": deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    accounts.at(strategy.governance(), force=True)
    accounts.at(strategy.strategist(), force=True)
    accounts.at(strategy.keeper(), force=True)
    accounts.at(strategy.guardian(), force=True)
    accounts.at(controller, force=True)

    chain.snapshot()

    # ===== Strategy =====
    # initialized = true

    # deposit: onlyAuthorizedActorsOrController
    authorizedActors = [
        strategy.governance(),
        strategy.strategist(),
        strategy.keeper(),
    ]

    with brownie.reverts("onlyAuthorizedActorsOrController"):
        strategy.deposit({"from": randomUser})

    for actor in authorizedActors:
        strategy.deposit({"from": actor})
        chain.revert()

    # harvest: onlyAuthorizedActors
    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    for actor in authorizedActors:
        strategy.harvest({"from": actor})
        chain.revert()

    # (if tendable) tend: onlyAuthorizedActors
    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        for actor in authorizedActors:
            chain.revert()
            strategy.tend({"from": actor})

    actorsToCheck = [
        randomUser,
        strategy.governance(),
        strategy.strategist(),
        strategy.keeper(),
    ]

    # withdrawAll onlyController
    for actor in actorsToCheck:
        with brownie.reverts("onlyController"):
            strategy.withdrawAll({"from": actor})

    # withdraw onlyController
    for actor in actorsToCheck:
        with brownie.reverts("onlyController"):
            strategy.withdraw(1, {"from": actor})

    # withdrawOther _onlyNotProtectedTokens
    for actor in actorsToCheck:
        with brownie.reverts("onlyController"):
            strategy.withdrawOther(controller, {"from": actor})

    authorizedPausers = [
        strategy.governance(),
        strategy.strategist(),
        strategy.guardian(),
    ]
    # pause onlyPausers
    for pauser in authorizedPausers:
        strategy.pause({"from": pauser})
        chain.revert()

    with brownie.reverts("onlyPausers"):
        strategy.pause({"from": randomUser})

    # unpause onlyPausers
    for pauser in authorizedPausers:
        strategy.pause({"from": pauser})
        strategy.unpause({"from": pauser})
        chain.revert()

    strategy.pause({"from": strategy.guardian()})
    with brownie.reverts("onlyPausers"):
        strategy.unpause({"from": randomUser})

    chain.revert()

    # Pause Gated Functions
    # deposit
    # withdraw
    # withdrawAll
    # withdrawOther
    # harvest
    # tend
    strategy.pause({"from": strategy.guardian()})
    with brownie.reverts("Pausable: paused"):
        sett.earn({"from": deployer})
    with brownie.reverts("Pausable: paused"):
        sett.withdrawAll({"from": deployer})
    with brownie.reverts("Pausable: paused"):
        strategy.harvest({"from": deployer})
    if strategy.isTendable():
        with brownie.reverts("Pausable: paused"):
            strategy.tend({"from": deployer})

    chain.revert()
    # Unpause should unlock
    # deposit
    # withdraw
    # withdrawAll
    # withdrawOther
    # harvest
    # tend
    strategy.pause({"from": strategy.guardian()})
    strategy.unpause({"from": strategy.guardian()})

    sett.deposit(1, {"from": deployer})
    sett.earn({"from": deployer})
    sett.withdraw(1, {"from": deployer})
    sett.withdrawAll({"from": deployer})
    strategy.harvest({"from": deployer})
    if strategy.isTendable():
        strategy.tend({"from": deployer})

    chain.revert()

    # Governance params: onlyGovernance
    # setGuardian
    # setWithdrawalFee
    # setPerformanceFeeStrategist
    # setPerformanceFeeGovernance
    # setController
    governance = strategy.governance()

    # Valid User should update
    strategy.setGuardian(AddressZero, {"from": governance})
    assert strategy.guardian() == AddressZero

    strategy.setWithdrawalFee(0, {"from": governance})
    assert strategy.withdrawalFee() == 0

    strategy.setPerformanceFeeStrategist(0, {"from": governance})
    assert strategy.performanceFeeStrategist() == 0

    strategy.setPerformanceFeeGovernance(0, {"from": governance})
    assert strategy.performanceFeeGovernance() == 0

    strategy.setController(AddressZero, {"from": governance})
    assert strategy.controller() == AddressZero

    # Invalid User should fail
    with brownie.reverts("onlyGovernance"):
        strategy.setGuardian(AddressZero, {"from": randomUser})

    with brownie.reverts("onlyGovernance"):
        strategy.setWithdrawalFee(0, {"from": randomUser})

    with brownie.reverts("onlyGovernance"):
        strategy.setPerformanceFeeStrategist(0, {"from": randomUser})

    with brownie.reverts("onlyGovernance"):
        strategy.setPerformanceFeeGovernance(0, {"from": randomUser})

    with brownie.reverts("onlyGovernance"):
        strategy.setController(AddressZero, {"from": randomUser})

    # Special fees: onlyGovernance
    # Pickle: setPicklePerformanceFeeGovernance
    # Pickle: setPicklePerformanceFeeStrategist
    if settId == "pickle.renCrv":
        strategy.setPicklePerformanceFeeGovernance(0, {"from": governance})
        assert strategy.picklePerformanceFeeGovernance() == 0

        strategy.setPicklePerformanceFeeStrategist(0, {"from": governance})
        assert strategy.picklePerformanceFeeStrategist() == 0

        with brownie.reverts("onlyGovernance"):
            strategy.setPicklePerformanceFeeGovernance(0, {"from": randomUser})

        with brownie.reverts("onlyGovernance"):
            strategy.setPicklePerformanceFeeStrategist(0, {"from": randomUser})

        # Harvest:
        # Harvest:
        if settId == "harvest.renCrv":
            strategy.setHarvestPerformanceFeeGovernance(0, {"from": governance})
            assert strategy.harvestPerformanceFeeGovernance() == 0

            strategy.setHarvestPerformanceFeeStrategist(0, {"from": governance})
            assert strategy.harvestPerformanceFeeStrategist() == 0

            with brownie.reverts("onlyGovernance"):
                strategy.setHarvestPerformanceFeeGovernance(0, {"from": randomUser})

            with brownie.reverts("onlyGovernance"):
                strategy.setHarvestPerformanceFeeStrategist(0, {"from": randomUser})

    chain.revert()

@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        # "native.badger",
        # "native.sbtcCrv",
        # "native.tbtcCrv",
        # "pickle.renCrv",
        # "harvest.renCrv",
        # "native.uniBadgerWbtc",
    ],
)
def test_sett_permissions(settId):
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


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        # "native.badger",
        # "native.sbtcCrv",
        # "native.tbtcCrv",
        # "pickle.renCrv",
        # "harvest.renCrv",
        # "native.uniBadgerWbtc",
    ],
)
def test_controller_permissions(settId):
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
    # approveStrategy onlyGovernance
    # revokeStrategy onlyGovernance
    # setRewards onlyGovernance
    # setSplit onlyGovernance
    # etOneSplit onlyGovernance
    assert False

