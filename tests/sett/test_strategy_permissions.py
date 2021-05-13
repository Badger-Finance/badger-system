from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import badger_single_sett, settTestConfig


def state_setup(badger, settConfig):
    settId = settConfig["id"]
    # TODO: Make this fetch based on the sett prefix name if it has dot
    controller = badger.getControllerFor(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)
    depositAmount = int(startingBalance * 0.8)
    assert startingBalance >= depositAmount
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    chain.sleep(days(1))
    chain.mine()

    sett.earn({"from": settKeeper})

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        strategy.tend({"from": strategyKeeper})

    strategy.harvest({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    accounts.at(badger.deployer, force=True)
    accounts.at(strategy.governance(), force=True)
    accounts.at(strategy.strategist(), force=True)
    accounts.at(strategy.keeper(), force=True)
    accounts.at(strategy.guardian(), force=True)
    accounts.at(controller, force=True)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_strategy_action_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)

    settId = settConfig["id"]

    controller = badger.getControllerFor(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    tendable = strategy.isTendable()

    deployer = badger.deployer
    randomUser = accounts[8]
    # End Setup

    # ===== Strategy =====
    authorizedActors = [
        strategy.governance(),
        strategy.keeper(),
    ]

    with brownie.reverts("onlyAuthorizedActorsOrController"):
        strategy.deposit({"from": randomUser})

    for actor in authorizedActors:
        strategy.deposit({"from": actor})

    # harvest: onlyAuthorizedActors
    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    for actor in authorizedActors:
        strategy.harvest({"from": actor})

    # (if tendable) tend: onlyAuthorizedActors
    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        for actor in authorizedActors:
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


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_strategy_config_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)

    settId = settConfig["id"]

    controller = badger.getControllerFor(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    tendable = strategy.isTendable()

    deployer = badger.deployer
    randomUser = accounts[8]
    # End Setup

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
    if settId == "harvest.renCrv":
        strategy.setFarmPerformanceFeeGovernance(0, {"from": governance})
        assert strategy.farmPerformanceFeeGovernance() == 0

        strategy.setFarmPerformanceFeeStrategist(0, {"from": governance})
        assert strategy.farmPerformanceFeeStrategist() == 0

        with brownie.reverts("onlyGovernance"):
            strategy.setFarmPerformanceFeeGovernance(0, {"from": randomUser})

        with brownie.reverts("onlyGovernance"):
            strategy.setFarmPerformanceFeeStrategist(0, {"from": randomUser})


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_strategy_pausing_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)

    settId = settConfig["id"]

    controller = badger.getControllerFor(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    tendable = strategy.isTendable()

    deployer = badger.deployer
    randomUser = accounts[8]
    # End Setup

    authorizedPausers = [
        strategy.governance(),
        strategy.guardian(),
    ]

    authorizedUnpausers = [
        strategy.governance(),
    ]

    # pause onlyPausers
    for pauser in authorizedPausers:
        strategy.pause({"from": pauser})
        strategy.unpause({"from": authorizedUnpausers[0]})

    with brownie.reverts("onlyPausers"):
        strategy.pause({"from": randomUser})

    # unpause onlyPausers
    for unpauser in authorizedUnpausers:
        strategy.pause({"from": unpauser})
        strategy.unpause({"from": unpauser})

    with brownie.reverts("onlyGovernance"):
        strategy.unpause({"from": randomUser})

    strategy.pause({"from": strategy.guardian()})

    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    with brownie.reverts("Pausable: paused"):
        sett.withdrawAll({"from": deployer})
    with brownie.reverts("Pausable: paused"):
        strategy.harvest({"from": strategyKeeper})
    if strategy.isTendable():
        with brownie.reverts("Pausable: paused"):
            strategy.tend({"from": strategyKeeper})

    strategy.unpause({"from": authorizedUnpausers[0]})

    sett.deposit(1, {"from": deployer})
    sett.withdraw(1, {"from": deployer})
    sett.withdrawAll({"from": deployer})

    strategy.harvest({"from": strategyKeeper})
    if strategy.isTendable():
        strategy.tend({"from": strategyKeeper})


@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_sett_pausing_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    settId = settConfig["id"]
    sett = badger.getSett(settId)
    deployer = badger.deployer
    randomUser = accounts[8]
    assert sett.strategist() == AddressZero
    # End Setup

    authorizedPausers = [
        sett.governance(),
        sett.guardian(),
    ]

    authorizedUnpausers = [
        sett.governance(),
    ]

    # pause onlyPausers
    for pauser in authorizedPausers:
        sett.pause({"from": pauser})
        sett.unpause({"from": authorizedUnpausers[0]})

    with brownie.reverts("onlyPausers"):
        sett.pause({"from": randomUser})

    # unpause onlyPausers
    for unpauser in authorizedUnpausers:
        sett.pause({"from": unpauser})
        sett.unpause({"from": unpauser})

    sett.pause({"from": sett.guardian()})
    with brownie.reverts("onlyGovernance"):
        sett.unpause({"from": randomUser})

    settKeeper = accounts.at(sett.keeper(), force=True)

    with brownie.reverts("Pausable: paused"):
        sett.earn({"from": settKeeper})
    with brownie.reverts("Pausable: paused"):
        sett.withdrawAll({"from": deployer})
    with brownie.reverts("Pausable: paused"):
        sett.withdraw(1, {"from": deployer})
    with brownie.reverts("Pausable: paused"):
        sett.deposit(1, {"from": randomUser})
    with brownie.reverts("Pausable: paused"):
        sett.depositAll({"from": randomUser})

    sett.unpause({"from": authorizedUnpausers[0]})

    sett.deposit(1, {"from": deployer})
    sett.earn({"from": settKeeper})
    sett.withdraw(1, {"from": deployer})
    sett.withdrawAll({"from": deployer})


@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_sett_config_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    settId = settConfig["id"]
    sett = badger.getSett(settId)
    randomUser = accounts[8]
    assert sett.strategist() == AddressZero
    # End Setup

    # == Governance ==
    validActor = sett.governance()

    # setMin
    with brownie.reverts("onlyGovernance"):
        sett.setMin(0, {"from": randomUser})

    sett.setMin(0, {"from": validActor})
    assert sett.min() == 0

    # setController
    with brownie.reverts("onlyGovernance"):
        sett.setController(AddressZero, {"from": randomUser})

    sett.setController(AddressZero, {"from": validActor})
    assert sett.controller() == AddressZero

    # setStrategist
    with brownie.reverts("onlyGovernance"):
        sett.setStrategist(validActor, {"from": randomUser})

    sett.setStrategist(validActor, {"from": validActor})
    assert sett.strategist() == validActor

    with brownie.reverts("onlyGovernance"):
        sett.setKeeper(validActor, {"from": randomUser})

    sett.setKeeper(validActor, {"from": validActor})
    assert sett.keeper() == validActor


@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_sett_earn_permissions(settConfig):
    # Setup
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    settId = settConfig["id"]
    sett = badger.getSett(settId)
    randomUser = accounts[8]
    assert sett.strategist() == AddressZero
    # End Setup

    # == Authorized Actors ==
    # earn

    authorizedActors = [
        sett.governance(),
        sett.keeper(),
    ]

    with brownie.reverts("onlyAuthorizedActors"):
        sett.earn({"from": randomUser})

    for actor in authorizedActors:
        chain.snapshot()
        sett.earn({"from": actor})
        chain.revert()


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_controller_permissions(settConfig):
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
    # setOneSplit onlyGovernance

    assert True
