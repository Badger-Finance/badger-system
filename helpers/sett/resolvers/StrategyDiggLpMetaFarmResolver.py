from brownie import interface
from rich.console import Console

from helpers.utils import snapBalancesMatchForToken
from .StrategyCoreResolver import StrategyCoreResolver

console = Console()


class StrategyDiggLpMetaFarmResolver(StrategyCoreResolver):
    def confirm_rebase(self, before, after, value):
        '''
        Lp token balance should stay the same.
        All DIGG balances should change in proportion to the rebase. (10% towards the new target)
        '''
        assert snapBalancesMatchForToken(before, after, "want")
        # TODO: Impl more accurate rebase checks.
        if value > 10**18:
            assert after.balances("digg", "user") > before.balances("digg", "user")
        elif value < 10**18:
            assert after.balances("digg", "user") < before.balances("digg", "user")

    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest ===")
        super().confirm_harvest(before, after, tx)

        # No staking position, strategy want should increase irrespective of
        # current balance.
        # TODO: Add more specific check that the correct reward amount was deposited.
        assert (
            after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")
        )

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        digg = interface.IERC20(strategy.digg())

        calls = self.add_entity_balances_for_tokens(calls, "digg", digg, entities)
        return calls

    def get_strategy_destinations(self):
        # No strategy destinations, uni lp stays in contract.
        return {}
