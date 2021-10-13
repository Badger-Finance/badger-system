import brownie
import pytest
import json
from brownie import (
    StrategyConvexStakingOptimizer,
    StrategyCvxHelper,
    StrategyCvxCrvHelper,
    Controller,
    accounts,
    Wei,
    interface,
)
from helpers.proxy_utils import deploy_proxy
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from config.badger_config import badger_config, digg_config, sett_config
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
from rich.console import Console
from helpers.token_utils import distribute_test_ether, distribute_from_whales

console = Console()

CRV_STRATS = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto2",
]

HELPER_STRATS = ["native.cvx","native.cvxCrv"]

NEW_STRATEGIES = {
    "native.renCrv": "0xe66dB6Eb807e6DAE8BD48793E9ad0140a2DEE22A",
    "native.sbtcCrv": "0x2f278515425c8eE754300e158116930B8EcCBBE1",
    "native.tbtcCrv": "0x9e0742EE7BECde52A5494310f09aad639AA4790B",
    "native.hbtcCrv": "0x7354D5119bD42a77E7162c8Afa8A1D18d5Da9cF8",
    "native.pbtcCrv": "0x3f98F3a21B125414e4740316bd6Ef14718764a22",
    "native.obtcCrv": "0x50Dd8A61Bdd11Cf5539DAA83Bc8E0F581eD8110a",
    "native.bbtcCrv": "0xf92660E0fdAfE945aa13616428c9fB4BE19f4d34",
    "native.tricrypto2": "0xf3202Aa2783F3DEE24a35853C6471db065B05D37",
    "native.cvxCrv": "0xf6D442Aead5960b283281A794B3e7d3605601247",
    "native.cvx": "0xc67129cf19BB00d60CC5CF62398fcA3A4Dc02a14",
}

@pytest.fixture()
def badger():
    return connect_badger(badger_config.prod_json)

@pytest.fixture()
def badger_deploy():
    with open(digg_config.prod_json) as f:
        return json.load(f)

@pytest.fixture()
def deployer(badger_deploy):
    return accounts.at(badger_deploy["deployer"], force=True)

@pytest.fixture()
def guardian(badger_deploy):
    return accounts.at(badger_deploy["guardian"], force=True)

@pytest.fixture()
def keeper(badger_deploy):
    return accounts.at(badger_deploy["keeper"], force=True)

@pytest.fixture()
def governance_multi(badger_deploy):
    return accounts.at(badger_deploy["devMultisig"], force=True)

@pytest.fixture()
def timelock(badger_deploy):
    return accounts.at(badger_deploy["timelock"], force=True)

@pytest.fixture()
def exp_controller(badger_deploy):
    return Controller.at(badger_deploy["sett_system"]["controllers"]["experimental"])

@pytest.fixture()
def native_controller(badger_deploy):
    return Controller.at(badger_deploy["sett_system"]["controllers"]["native"])


@pytest.mark.parametrize(
    "strategy_key",
    CRV_STRATS,
)
def test_migrate_staking_optimizer(
    badger, 
    strategy_key,
    governance_multi,
    timelock,
    exp_controller,
    native_controller,
    deployer,
    ):

    # Different Setts use different controllers:
    if strategy_key in ["native.renCrv", "native.sbtcCrv", "native.tbtcCrv"]:
        governance = timelock
        controller = native_controller
    else:
        governance = governance_multi
        controller = exp_controller

    console.print(f"[yellow]Processing {strategy_key}...[/yellow]")

    # Get current strategy
    strategy = badger.getStrategy(strategy_key)
    # Get vault
    vault = badger.getSett(strategy_key)
    # Get new strategy
    newStrategy = StrategyConvexStakingOptimizer.at(NEW_STRATEGIES[strategy_key])
    # Get want
    want = interface.IERC20(strategy.want())

    console.print(f"[blue]Current Strategy: [/blue]{strategy.address}")
    console.print(f"[blue]New Strategy: [/blue]{newStrategy.address}")
    console.print(f"[blue]Vault: [/blue]{vault.address}")
    console.print(f"[blue]Want: [/blue]{want.address}")

    # ==== Parameter comparison ==== #

    # Want matches vault and new Strategy
    assert want == vault.token()
    assert want == newStrategy.want()

    # Current strategy shouldnt posses these methods
    with brownie.reverts():
        strategy.crvCvxCrvSlippageToleranceBps()

    with brownie.reverts():
        strategy.crvCvxCrvPoolIndex()

    # Check that Slippage tolerance was set on init for new Strategy
    assert newStrategy.crvCvxCrvSlippageToleranceBps() == 500
    assert newStrategy.crvCvxCrvPoolIndex() == 2

    # Check that strategy's constants remain the same
    assert newStrategy.baseRewardsPool() == strategy.baseRewardsPool()
    assert newStrategy.pid() == strategy.pid()
    assert newStrategy.badgerTree() == strategy.badgerTree()
    assert newStrategy.cvxHelperVault() == strategy.cvxHelperVault()
    assert newStrategy.cvxCrvHelperVault() == strategy.cvxCrvHelperVault()
    assert newStrategy.curvePool() == strategy.curvePool()
    assert newStrategy.autoCompoundingBps() == strategy.autoCompoundingBps()
    assert (
        newStrategy.autoCompoundingPerformanceFeeGovernance()
        == newStrategy.autoCompoundingPerformanceFeeGovernance()
    )
    assert newStrategy.autoCompoundingPerformanceFeeGovernance() == (
        newStrategy.autoCompoundingPerformanceFeeGovernance()
    )

    # Check that strategy's parameters remain the same
    assert newStrategy.want() == strategy.want()
    assert newStrategy.strategist() == "0x86cbD0ce0c087b482782c181dA8d191De18C8275" # Tech Ops Multisig
    assert newStrategy.keeper() == "0x711A339c002386f9db409cA55b6A35a604aB6cF6" # Keeper ACL
    assert newStrategy.guardian() == "0x6615e67b8B6b6375D38A0A3f937cd8c1a1e96386" # WarRoom ACL

    assert newStrategy.performanceFeeGovernance() == strategy.performanceFeeGovernance()
    assert newStrategy.performanceFeeStrategist() == strategy.performanceFeeStrategist()
    assert newStrategy.withdrawalFee() == strategy.withdrawalFee()
    console.print('\n', f"[green]Fees Match![/green]")
    console.print(f"GovPerformance: {strategy.performanceFeeGovernance()}")
    console.print(f"StrategistPerformance: {strategy.performanceFeeStrategist()}")
    console.print(f"Withdrawal: {strategy.withdrawalFee()}")

    # ==== Pre-Migration checks ==== #

    # Balance of Sett (Balance on Sett, Controller and Strategy) is greater than 0
    initialSettBalance = vault.balance()
    assert initialSettBalance > 0
    # Balance of vault equals to the Sett's balance minus strategy balance
    assert (
        want.balanceOf(vault.address)
        == initialSettBalance - strategy.balanceOf()
    )
    # Balance of new Strategy starts off at 0
    assert newStrategy.balanceOf() == 0
    # PPFS before migration
    ppfs = vault.getPricePerFullShare()

    # ==== Migration ==== #
    migrate_strategy(
        badger,
        strategy,
        newStrategy,
        strategy_key, 
        controller,
        governance,
    )

    # ==== Post-Migration checks ==== #

    # Balance of Sett remains the same
    assert initialSettBalance == vault.balance()
    # Balance of vault equals to the whole Sett balance since controller withdraws all of want
    # and this is transfered to the vault.
    assert want.balanceOf(vault.address) == initialSettBalance
    # Balance of old Strategy goes down to 0
    assert strategy.balanceOf() == 0
    # Balance of new Strategy starts off at 0
    assert newStrategy.balanceOf() == 0
    # PPS remain the same post migration
    assert ppfs == vault.getPricePerFullShare()

    console.print(f"[green]Strategy migrated successfully![/green]")


    # ==== Run tests ==== #

    # distribute_test_assets(strategy_key, deployer)

    # sett_config = {"id": strategy_key, "mode": "test"}

    # assert_deposit_withdraw_single_user_flow(sett_config)
    # assert_single_user_harvest_flow(sett_config)
    # assert_migrate_single_user(sett_config)
    # assert_withdraw_other(sett_config)
    # assert_single_user_harvest_flow_remove_fees(sett_config)

    # assert_strategy_action_permissions(sett_config)
    # assert_strategy_config_permissions(sett_config)
    # assert_strategy_pausing_permissions(sett_config)
    # assert_sett_pausing_permissions(sett_config)
    # assert_sett_config_permissions(sett_config)
    # assert_controller_permissions(sett_config)

def distribute_test_assets(strategy_key, deployer):
    distribute_test_ether(deployer, Wei("20 ether"))

    # Deploy and initialize the strategy
    if strategy_key == "native.renCrv":
        distribute_from_whales(deployer, 1, "renCrv")
    if strategy_key == "native.sbtcCrv":
        distribute_from_whales(deployer, 1, "sbtcCrv")
    if strategy_key == "native.tbtcCrv":
        distribute_from_whales(deployer, 1, "tbtcCrv")
    if strategy_key == "native.hbtcCrv":
        distribute_from_whales(deployer, 1, "hbtcCrv")
    if strategy_key == "native.pbtcCrv":
        distribute_from_whales(deployer, 1, "pbtcCrv")
    if strategy_key == "native.obtcCrv":
        distribute_from_whales(deployer, 1, "obtcCrv")
    if strategy_key == "native.bbtcCrv":
        distribute_from_whales(deployer, 1, "bbtcCrv")
    if strategy_key == "native.tricrypto2":
        distribute_from_whales(deployer, 1, "tricrypto2")


def migrate_strategy(
    badger,
    strategy,
    newStrategy,
    key, 
    controller,
    governance
):
    console.print(f"[blue]Migrating strategy[/blue]")
    # Approve new strategy for want on Controller
    controller.approveStrategy(strategy.want(), newStrategy.address, {"from": governance})
    assert controller.approvedStrategies(strategy.want(), newStrategy.address)

    # Set new strategy for want on Controller
    controller.setStrategy(strategy.want(), newStrategy.address, {"from": governance})
    assert controller.strategies(strategy.want()) == newStrategy.address

    # Add new strategy to Badger System to be able to run tests
    badger.sett_system.strategies[key] = newStrategy

