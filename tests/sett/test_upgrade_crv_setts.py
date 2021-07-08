import pytest
from brownie import Contract, chain, interface
from rich.console import Console

from helpers.sett.SnapshotManager import SnapshotManager
from helpers.sett.simulation.SimulationManager import SimulationManager
from helpers.registry import registry
from helpers.registry.artifacts import artifacts
from helpers.time_utils import days
from helpers.token_utils import distribute_from_whales
from scripts.upgrade.upgrade_crv_setts import (
    queue_upgrade_crv_strat,
    CRV_SETTS_TO_UPGRADE,
)
from scripts.systems.badger_system import connect_badger
from tests.sett.generic_strategy_tests.strategy_flow import (
    assert_deposit_withdraw_single_user_flow,
    assert_single_user_harvest_flow,
    assert_migrate_single_user,
    assert_withdraw_other,
    assert_single_user_harvest_flow_remove_fees,
)
from tests.sett.generic_strategy_tests.strategy_permissions import (
    assert_strategy_action_permissions,
    assert_strategy_config_permissions,
    assert_strategy_pausing_permissions,
    assert_sett_pausing_permissions,
    assert_sett_config_permissions,
    assert_controller_permissions,
)
from tests.conftest import badger_single_sett
from config.badger_config import badger_config

console = Console()


@pytest.mark.parametrize(
    "settID",
    CRV_SETTS_TO_UPGRADE,
)
def test_simulation_after_upgrade_crv_setts(settID):
    # Upgrade crv strategy
    badger = connect_badger(badger_config.prod_json)

    """
    TODO Get the Implementation before upgrade
    """

    txFilename = queue_upgrade_crv_strat(badger, settID)
    # Sleep 2 days to pass timelock delay period.
    chain.sleep(2 * days(2))
    badger.governance_execute_transaction(txFilename)

    """
    TODO assert tht implementation has changed
    """

    ## Object representing the sett we want and the mode we're in
    thisSettConfig = {"id": settID, "mode": "test"}

    ## Get badger so we can get info in sett and strats
    badger = badger_single_sett(thisSettConfig)

    ## We now have the want, we can mint some
    deployer = badger.deployer

    ## Mints token for us
    distribute_from_whales(deployer)

    snap = SnapshotManager(badger, settID)
    simulation = SimulationManager(badger, snap, settID)

    simulation.provision()
    # Randomize 30 actions.
    simulation.randomize(30)
    simulation.run()

    assert_deposit_withdraw_single_user_flow(thisSettConfig)
    assert_single_user_harvest_flow(thisSettConfig)
    assert_migrate_single_user(thisSettConfig)
    assert_withdraw_other(thisSettConfig)
    assert_single_user_harvest_flow_remove_fees(thisSettConfig)

    assert_strategy_action_permissions(thisSettConfig)
    assert_strategy_config_permissions(thisSettConfig)
    assert_strategy_pausing_permissions(thisSettConfig)
    assert_sett_pausing_permissions(thisSettConfig)
    assert_sett_config_permissions(thisSettConfig)
    assert_controller_permissions(thisSettConfig)
