import brownie
import pytest
from brownie import StrategyConvexStakingOptimizer

from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger

STRATEGIES = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto2",
]


@pytest.mark.parametrize(
    "strategy_key",
    STRATEGIES,
)
def test_upgrade_convex_strats(strategy_key):
    badger = connect_badger(badger_config.prod_json)

    # NOTE: Ideally should get deployed contract/abi from etherscan,
    #       but Contract.from_explorer() doesn't seem to work
    strategy = badger.getStrategy(strategy_key)

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


def upgrade_strategy(badger, strategy, name, artifact):
    # Deploy new logic
    badger.deploy_logic(name, artifact)
    logic = badger.logic[name]

    badger.devProxyAdmin.upgrade(
        strategy,
        logic,
        {"from": badger.governanceTimelock},
    )
