import pytest
from brownie import (
    accounts,
    chain,
    reverts,
)
from rich.console import Console

from helpers.time_utils import days
from helpers.constants import MaxUint256
from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from helpers.sett.SimulationManager import SimulationManager
from tests.conftest import badger_single_sett, diggSettTestConfig
from config.badger_config import digg_decimals
console = Console()


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", diggSettTestConfig,
)
def test_simulation(settConfig):
    badger = badger_single_sett(settConfig)
    snap = DiggSnapshotManager(badger, settConfig["id"])
    simulation = SimulationManager(badger, snap, settConfig["id"])

    assert False
