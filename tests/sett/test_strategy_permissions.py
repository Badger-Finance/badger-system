import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import settTestConfig
from tests.sett.generic_strategy_tests.strategy_permissions import (
    assert_strategy_action_permissions,
    assert_strategy_config_permissions,
    assert_strategy_pausing_permissions,
    assert_sett_pausing_permissions,
    assert_sett_config_permissions,
    assert_sett_earn_permissions,
    assert_controller_permissions,
)

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_strategy_action_permissions(settConfig):
    assert_strategy_action_permissions(settConfig)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_strategy_config_permissions(settConfig):
    assert_strategy_config_permissions(settConfig)


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
    sett.pause({"from": strategy.guardian()})

    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    with brownie.reverts("Pausable: paused"):
        sett.withdrawAll({"from": deployer})
    with brownie.reverts("Pausable: paused"):
        strategy.harvest({"from": strategyKeeper})
    if strategy.isTendable():
        with brownie.reverts("Pausable: paused"):
            strategy.tend({"from": strategyKeeper})

    strategy.unpause({"from": authorizedUnpausers[0]})
    sett.unpause({"from": authorizedUnpausers[0]})

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
def test_config_permissions(settConfig):
    assert_sett_config_permissions(settConfig)


@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_sett_earn_permissions(settConfig):
    assert_sett_earn_permissions(settConfig)


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_controller_permissions(settConfig):
    assert_controller_permissions(settConfig)
