import pytest

from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from tests.conftest import badger_single_sett, settTestConfig


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_simulation(settConfig):
    # connect to prod deploy and run simulation
    badger = badger_single_sett(settConfig, deploy=False)
    snap = SnapshotManager(badger, settConfig["id"])
    simulation = SimulationManager(badger, snap, settConfig["id"])

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()
