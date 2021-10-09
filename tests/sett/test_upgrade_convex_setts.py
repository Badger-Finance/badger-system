import brownie
import pytest
from brownie import (
    StrategyConvexStakingOptimizer,
    StrategyCvxHelper,
    StrategyCvxCrvHelper,
)

from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
# from tests.sett.generic_strategy_tests.strategy_flow import (
#     assert_deposit_withdraw_single_user_flow,
#     assert_single_user_harvest_flow,
#     assert_migrate_single_user,
#     assert_withdraw_other,
#     assert_single_user_harvest_flow_remove_fees,
# )
# from tests.sett.generic_strategy_tests.strategy_permissions import (
#     assert_strategy_action_permissions,
#     assert_strategy_config_permissions,
#     assert_strategy_pausing_permissions,
#     assert_sett_pausing_permissions,
#     assert_sett_config_permissions,
#     assert_controller_permissions,
# )

CRV_STRATS = [
    # "native.renCrv",
    "native.sbtcCrv",
    # "native.tbtcCrv",
    # "native.hbtcCrv",
    # "native.pbtcCrv",
    # "native.obtcCrv",
    # "native.bbtcCrv",
    # "native.tricrypto2",
]

HELPER_STRATS = {
    "native.cvx": {
        "name": "StrategyCvxHelper",
        "artifact": StrategyCvxHelper,
    },
    "native.cvxCrv": {
        "name": "StrategyCvxCrvHelper",
        "artifact": StrategyCvxCrvHelper,
    },
}


def upgrade_strategy(badger, strategy, name, artifact):
    # Deploy new logic
    badger.deploy_logic(name, artifact)
    logic = badger.logic[name]

    badger.devProxyAdmin.upgrade(
        strategy,
        logic,
        {"from": badger.governanceTimelock},
    )


@pytest.fixture()
def badger():
    return connect_badger(badger_config.prod_json)


@pytest.mark.parametrize(
    "strategy_key",
    CRV_STRATS,
)
def test_upgraded_convex_strats_storage(badger, strategy_key):
    # NOTE: Ideally should get deployed contract/abi from etherscan,
    #       but Contract.from_explorer() doesn't seem to work
    strategy = badger.getStrategy(strategy_key)

    with brownie.reverts():
        strategy.crvCvxCrvSlippageToleranceBps()

    with brownie.reverts():
        strategy.crvCvxCrvPoolIndex()

    # TODO: There's probably a better way to do this
    baseRewardsPool = strategy.baseRewardsPool()
    pid = strategy.pid()
    badgerTree = strategy.badgerTree()
    cvxHelperVault = strategy.cvxHelperVault()
    cvxCrvHelperVault = strategy.cvxCrvHelperVault()
    curvePool = strategy.curvePool()
    autoCompoundingBps = strategy.autoCompoundingBps()
    autoCompoundingPerformanceFeeGovernance = (
        strategy.autoCompoundingPerformanceFeeGovernance()
    )
    autoCompoundingPerformanceFeeGovernance = (
        strategy.autoCompoundingPerformanceFeeGovernance()
    )

    upgrade_strategy(
        badger,
        strategy,
        "StrategyStakingConvexOptimizer",
        StrategyConvexStakingOptimizer,
    )

    # Check that it's upgraded
    assert strategy.crvCvxCrvPoolIndex() == 2
    assert strategy.crvCvxCrvSlippageToleranceBps() == 0

    assert baseRewardsPool == strategy.baseRewardsPool()
    assert pid == strategy.pid()
    assert badgerTree == strategy.badgerTree()
    assert cvxHelperVault == strategy.cvxHelperVault()
    assert cvxCrvHelperVault == strategy.cvxCrvHelperVault()
    assert curvePool == strategy.curvePool()
    assert autoCompoundingBps == strategy.autoCompoundingBps()
    assert (
        autoCompoundingPerformanceFeeGovernance
        == strategy.autoCompoundingPerformanceFeeGovernance()
    )
    assert autoCompoundingPerformanceFeeGovernance == (
        strategy.autoCompoundingPerformanceFeeGovernance()
    )

    # Set slippage tolerance
    strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": strategy.governance()})
    assert strategy.crvCvxCrvSlippageToleranceBps() == 500


@pytest.mark.parametrize(
    "strategy_key",
    HELPER_STRATS.keys(),
)
def test_upgraded_helper_strats_storage(strategy_key, badger):
    # NOTE: Ideally should get deployed contract/abi from etherscan,
    #       but Contract.from_explorer() doesn't seem to work
    strategy = badger.getStrategy(strategy_key)

    with brownie.reverts():
        strategy.crvCvxCrvPoolIndex()

    with brownie.reverts():
        strategy.crvCvxCrvSlippageToleranceBps()

    upgrade_strategy(
        badger,
        strategy,
        HELPER_STRATS[strategy_key]["name"],
        HELPER_STRATS[strategy_key]["artifact"],
    )

    assert strategy.crvCvxCrvPoolIndex() == 2
    assert strategy.crvCvxCrvSlippageToleranceBps() == 0

    # Set slippage tolerance
    strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": strategy.governance()})
    assert strategy.crvCvxCrvSlippageToleranceBps() == 500


# NOTE: Doesn't work
@pytest.mark.skip()
@pytest.mark.parametrize(
    "strategy_key",
    CRV_STRATS,
)
def test_upgraded_convex_strats(badger, strategy_key):
    # NOTE: Ideally should get deployed contract/abi from etherscan,
    #       but Contract.from_explorer() doesn't seem to work
    strategy = badger.getStrategy(strategy_key)

    upgrade_strategy(
        badger,
        strategy,
        "StrategyStakingConvexOptimizer",
        StrategyConvexStakingOptimizer,
    )

    # Run tests
    sett_config = {"id": strategy_key, "mode": "test"}

    assert_deposit_withdraw_single_user_flow(sett_config)
    assert_single_user_harvest_flow(sett_config)
    assert_migrate_single_user(sett_config)
    assert_withdraw_other(sett_config)
    assert_single_user_harvest_flow_remove_fees(sett_config)

    assert_strategy_action_permissions(sett_config)
    assert_strategy_config_permissions(sett_config)
    assert_strategy_pausing_permissions(sett_config)
    assert_sett_pausing_permissions(sett_config)
    assert_sett_config_permissions(sett_config)
    assert_controller_permissions(sett_config)
