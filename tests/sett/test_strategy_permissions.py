import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import settTestConfig
from tests.sett.generic_strategy_tests.strategy_permissions import (
    assert_strategy_action_permissions,
    assert_strategy_config_permissions,
    assert_strategy_pausing_permissions,
    assert_sett_pausing_permissions,
    assert_sett_config_permissions,
    assert_sett_earn_permissions,
    assert_controller_permissions
)

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_strategy_action_permissions(settConfig):
    assert_strategy_action_permissions(settConfig)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_strategy_config_permissions(settConfig):
    assert_strategy_config_permissions(settConfig)

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_strategy_pausing_permissions(settConfig):
    assert_strategy_pausing_permissions(settConfig)


@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_sett_pausing_permissions(settConfig):
    assert_sett_pausing_permissions(settConfig)

@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_config_permissions(settConfig):
    assert_sett_config_permissions(settConfig)


@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_sett_earn_permissions(settConfig):
    assert_sett_earn_permissions(settConfig)


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_controller_permissions(settConfig):
    assert_controller_permissions(settConfig)
