import pytest

from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from tests.conftest import badger_single_sett, diggSettTestConfig


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", diggSettTestConfig,
)
def test_simulation(settConfig):
    badger = badger_single_sett(settConfig)
    snap = DiggSnapshotManager(badger, settConfig["id"])
    simulation = SimulationManager(badger, snap, settConfig["id"])

    simulation.provision()
    # Randomize 100 actions.
    simulation.randomize(100)
    simulation.run()
