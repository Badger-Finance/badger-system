from brownie import interface
from tabulate import tabulate
from rich.console import Console

from helpers.utils import val, snapBalancesMatchForToken
from config.badger_config import digg_decimals
from .StrategyCoreResolver import StrategyCoreResolver
from .StrategyBaseSushiResolver import StrategyBaseSushiResolver

console = Console()


class StrategySushiDiggWbtcLpOptimizerResolver(StrategyBaseSushiResolver, StrategyCoreResolver):
    def confirm_rebase(self, before, after, value):
        '''
        Lp token balance should stay the same.
        Sushi balances stay the same.
        xSushi balances stay the same.
        All DIGG balances should change in proportion to the rebase. (10% towards the new target)
        '''
        assert snapBalancesMatchForToken(before, after, "want")
        assert snapBalancesMatchForToken(before, after, "sushi")
        assert snapBalancesMatchForToken(before, after, "xsushi")
        # TODO: Impl more accurate rebase checks.
        if value > 10**digg_decimals:
            assert after.balances("digg", "user") > before.balances("digg", "user")
        elif value < 10**digg_decimals:
            assert after.balances("digg", "user") < before.balances("digg", "user")

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        digg = interface.IERC20(strategy.digg())

        calls = self.add_entity_balances_for_tokens(calls, "digg", digg, entities)
        return calls
