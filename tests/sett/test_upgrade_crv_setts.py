import pytest
from brownie import chain, interface

from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from helpers.gnosis_safe import GnosisSafe
from helpers.time_utils import days
from scripts.upgrade.upgrade_crv_setts import (
    queue_upgrade_crv_sett,
    CRV_SETTS_TO_UPGRADE,
)
from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.badger_config import badger_config


@pytest.mark.parametrize(
    "settID", CRV_SETTS_TO_UPGRADE,
)
def test_simulation_after_upgrade_crv_setts(settID):
    # Upgrade crv setts kkk
    badger = connect_badger(badger_config.prod_json)
    txFilename = queue_upgrade_crv_sett(badger, settID)
    # Sleep 2 days to pass timelock delay period.
    chain.sleep(2 * days(2))
    badger.governance_execute_transaction(txFilename)
    sett = interface.ISett("0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545")

    snap = SnapshotManager(badger, settID)
    simulation = SimulationManager(badger, snap, settID)

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()
