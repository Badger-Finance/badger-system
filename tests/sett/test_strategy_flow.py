import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import settTestConfig

from tests.sett.generic_strategy_tests.strategy_flow import (
    assert_deposit_withdraw_single_user_flow,
    assert_single_user_harvest_flow,
    assert_migrate_single_user,
    assert_withdraw_other,
    assert_single_user_harvest_flow_remove_fees,
)


@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_deposit_withdraw_single_user_flow(settConfig):
    assert_deposit_withdraw_single_user_flow(settConfig)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_single_user_harvest_flow(settConfig):
    assert_single_user_harvest_flow(settConfig)


@pytest.mark.parametrize("settConfig", settTestConfig)
def test_migrate_single_user(settConfig):
    assert_migrate_single_user(settConfig)


@pytest.mark.parametrize("settConfig", settTestConfig)
def test_withdraw_other(settConfig):
    assert_withdraw_other(settConfig)


@pytest.mark.parametrize("settConfig", settTestConfig)
def test_single_user_harvest_flow_remove_fees(settConfig):
    assert_single_user_harvest_flow_remove_fees(settConfig)
