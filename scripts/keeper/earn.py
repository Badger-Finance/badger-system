from helpers.utils import val
from brownie import *
from config.keeper import keeper_config
from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()


gas_strategies.set_default_for_active_chain()


def get_expected_strategy_deposit_location(badger: BadgerSystem, id):
    if id == "native.badger":
        # Rewards Staking
        return badger.getSettRewards("native.badger")
    if id == "native.uniBadgerWbtc":
        # Rewards Staking
        return badger.getSettRewards("native.uniBadgerWbtc")
    if id == "native.renCrv":
        # CRV Gauge
        return registry.curve.pools.renCrv.gauge
    if id == "native.sbtcCrv":
        # CRV Gauge
        return registry.curve.pools.sbtcCrv.gauge
    if id == "native.tbtcCrv":
        # CRV Gauge
        return registry.curve.pools.tbtcCrv.gauge
    if id == "harvest.renCrv":
        # Harvest Vault
        return registry.harvest.vaults.renCrv
    if id == "native.sushiWbtcEth":
        # Sushi Chef
        return registry.sushi.sushiChef
    if id == "native.sushiBadgerWbtc":
        # Sushi Chef
        return registry.sushi.sushiChef


def earn_preconditions(key, vaultBalance, strategyBalance):
    has_override = keeper_config.has_earn_threshold_override_active_chain(key)
    override_threshold = keeper_config.get_active_chain_earn_threshold_override(key)

    # Always allow earn on first run
    if strategyBalance == 0:
        console.print("No strategy balance, earn()")
        return True
    # Earn if deposits have accumulated over a static threshold
    if has_override and vaultBalance >= override_threshold:
        console.print(
            f"Vault balance of {vaultBalance} over earn threshold override of {override_threshold} for {key}"
        )
        return True
    # Earn if deposits have accumulated over % threshold
    if vaultBalance / strategyBalance > keeper_config.earn_default_percentage_threshold:
        console.print(
            f"Vault balance of {vaultBalance} and strategyBalance of {strategyBalance} over standard % threshold of {keeper_config.earn_default_percentage_threshold} for {key}"
        )

        return True
    else:
        console.print(
            {
                "vaultBalance": vaultBalance,
                "strategyBalance": strategyBalance,
                "has_override": has_override,
                "override_threshold": override_threshold,
                "standard_threshold_pct": keeper_config.earn_default_percentage_threshold,
                "vault_to_strategy_ratio": vaultBalance / strategyBalance,
            }
        )
        return False


def earn_all(badger: BadgerSystem, skip):
    for key, vault in badger.sett_system.vaults.items():
        if key in skip:
            print("Skip ", key)
            continue
        console.print("\n[bold red]===== Earn: " + key + " =====[/bold red]\n")
        strategy = badger.getStrategy(key)
        controller = Controller.at(vault.controller())
        want = interface.IERC20(vault.token())

        # Pre safety checks
        assert want == strategy.want()
        assert strategy.controller() == controller
        assert vault.controller() == controller
        assert controller.strategies(want) == strategy

        vaultBefore = want.balanceOf(vault)
        strategyBefore = strategy.balanceOf()

        toEarn = False
        if earn_preconditions(key, vaultBefore, strategyBefore):
            print("Earn: " + key, vault, strategy)
            toEarn = True

            snap = SnapshotManager(badger, key)
            before = snap.snap()

            keeper = badger.earner
            snap.settEarnAcl(
                vault,
                {"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
            )

            after = snap.snap()
            snap.printCompare(before, after)


def main():
    # TODO: Output message when failure

    badger = connect_badger(load_keeper=True)
    skip = keeper_config.get_active_chain_skipped_setts("earn")
    earn_all(badger, skip)
