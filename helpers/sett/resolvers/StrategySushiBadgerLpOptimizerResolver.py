from brownie import *

from helpers.constants import *
from helpers.multicall import Call, func, as_wei
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver

def confirm_harvest_badger_lp(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle BADGER to zero
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf >= before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


class StrategySushiBadgerLpOptimizerResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after):
        super().confirm_harvest(before, after)
        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert after.get("strategy.balanceOf") >= before_balance if before_balance else 0

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

        # Sushi in badger tree should increase
        # Strategy should have no sushi
        # Strategy should have no sushi in Chef

    
    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        sushi = interface.IERC20(strategy.sushi())
        xsushi = interface.IERC20(strategy.xsushi())

        calls = self.add_entity_balances_for_tokens(calls, "sushi", sushi, entities)
        calls = self.add_entity_balances_for_tokens(calls, "xsushi", xsushi, entities)
        return calls

    def add_strategy_snap(self, calls):
        super().add_strategy_snap(calls)

        strategy = self.manager.strategy

        # Want staked in Chef
        calls.append(
            Call(
                strategy.chef(),
                [func.rewardPool.balanceOf, strategy.address],
                [["metaFarm.staked.strategy", as_wei]],
            )
        )

        # Sushi staked in SushiBar
        calls.append(
            Call(
                strategy.xsushi(),
                [func.rewardPool.balanceOf, strategy.address],
                [["metaFarm.staked.strategy", as_wei]],
            )
        )



        return calls

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {"chef": strategy.chef(), "bar": strategy.xsushi()}