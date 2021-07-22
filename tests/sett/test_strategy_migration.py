import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import settTestConfig, badger_single_sett
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.strategy_registry import name_to_artifact, contract_name_to_artifact

@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_strategy_migration(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    print("Testing Migration of ", settConfig["id"])
    print("Current Strategy: ", strategy.address)


