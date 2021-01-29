import pytest

from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from tests.conftest import badger_single_sett, settTestConfig
from scripts.systems.constants import SyncFeeType


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_simulation(settConfig):
    # connect to prod deploy and run simulation
    settID = settConfig["id"]
    badger = badger_single_sett(settConfig, deploy=False, upgrade=True)
    badger.syncWithdrawalFees(settID, syncFeeType=SyncFeeType.CONSTANT)
    snap = SnapshotManager(badger, settID)
    simulation = SimulationManager(badger, snap, settID)

    simulation.provision()
    # Randomize 100 actions.
    simulation.randomize(100)
    simulation.run()
