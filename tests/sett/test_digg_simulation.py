import pytest

from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from tests.conftest import badger_single_sett, diggSettTestConfig
from scripts.systems.constants import SyncFeeType


@pytest.mark.parametrize(
    "settConfig", diggSettTestConfig,
)
def test_digg_simulation_constant_fee(settConfig):
    # connect to prod deploy and run simulation
    settID = settConfig["id"]
    badger = badger_single_sett(settConfig, deploy=False, upgrade=True)
    badger.syncWithdrawalFees(settID, syncFeeType=SyncFeeType.CONSTANT)
    snap = DiggSnapshotManager(badger, settID)
    simulation = SimulationManager(badger, snap, settID, seed=1611893572)

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()


@pytest.mark.skip()
# @pytest.mark.parametrize(
#     "settConfig", diggSettTestConfig,
# )
def test_digg_simulation_zero_fee(settConfig):
    # connect to prod deploy and run simulation
    settID = settConfig["id"]
    badger = badger_single_sett(settConfig, deploy=False, upgrade=True)
    badger.syncWithdrawalFees(settID, syncFeeType=SyncFeeType.ZERO)
    snap = DiggSnapshotManager(badger, settID)
    simulation = SimulationManager(badger, snap, settID)

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()
