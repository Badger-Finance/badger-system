import pytest
from brownie import chain

from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from helpers.time_utils import days
from scripts.upgrade.upgrade_sushi_strategies import (
    queue_upgrade_strategy,
    SUSHI_STRATEGIES_TO_UPGRADE,
)
from scripts.systems.badger_system import connect_badger
from config.badger_config import badger_config


@pytest.mark.parametrize(
    "args", SUSHI_STRATEGIES_TO_UPGRADE,
)
def test_simulation_after_upgrade_sushi_strategies(args):
    (strategyID, artifactName) = args
    # Upgrade crv setts kkk
    badger = connect_badger(badger_config.prod_json)
    txFilename = queue_upgrade_strategy(badger, strategyID, artifactName)
    # Sleep 2 days to pass timelock delay period.
    chain.sleep(2 * days(2))
    badger.governance_execute_transaction(txFilename)

    # NB: strategy/sett IDs align
    snap = SnapshotManager(badger, strategyID)
    simulation = SimulationManager(badger, snap, strategyID)

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()
