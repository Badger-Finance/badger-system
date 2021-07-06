import pytest
from brownie import *
from helpers.time_utils import days
from helpers.constants import MaxUint256
from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from tests.conftest import badger_single_sett, stabilizeTestConfig

@pytest.mark.parametrize(
    "settConfig", stabilizeTestConfig,
)
def test_single_user_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.vault
    strategy = badger.strategy
    controller = badger.controller

    want = interface.IDigg(strategy.want())

    print("Sett", sett.address)
    print("strategy", strategy.address)
    print("controller", controller.address)
    print("want", want.address)

    assert False
