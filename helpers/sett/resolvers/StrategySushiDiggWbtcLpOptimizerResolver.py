from brownie import interface
from rich.console import Console

from helpers.utils import snapBalancesMatchForToken
from .StrategyBaseSushiResolver import StrategyBaseSushiResolver

console = Console()


class StrategySushiDiggWbtcLpOptimizerResolver(StrategyBaseSushiResolver):
    def confirm_rebase(self, before, after, value):
        """
        Lp token balance should stay the same.
        Sushi balances stay the same.
        xSushi balances stay the same.
        """
        super().confirm_rebase(before, after, value)
        assert snapBalancesMatchForToken(before, after, "want")
        assert snapBalancesMatchForToken(before, after, "sushi")
        assert snapBalancesMatchForToken(before, after, "xsushi")

    def add_balances_snap(self, calls, entities):
        calls = super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        digg = interface.IERC20(strategy.digg())

        calls = self.add_entity_balances_for_tokens(calls, "digg", digg, entities)
        calls = self.add_entity_shares_for_tokens(calls, "digg", digg, entities)
        return calls
