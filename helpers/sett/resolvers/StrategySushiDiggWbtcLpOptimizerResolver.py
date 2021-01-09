from brownie import *
from tabulate import tabulate
from rich.console import Console

from helpers.utils import val
from helpers.constants import *
from helpers.multicall import Call, func, as_wei
from helpers.sett.resolvers.StrategyDiggCoreResolver import StrategyDiggCoreResolver

console = Console()


class StrategySushiDiggWbtcLpOptimizerResolver(StrategyDiggCoreResolver):
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest ===")
        self.manager.printCompare(before, after)
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert after.get("strategy.balanceOf") >= before_balance if before_balance else 0

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

        # Sushi in badger tree should increase

        # Strategy should have no sushi

        # Strategy should have no sushi in Chef

    def printHarvestState(self, tx):

        events = tx.events
        event = events['HarvestState'][0]

        xSushiHarvested = event['xSushiHarvested']
        totalxSushi = event['totalxSushi']
        toStrategist = event['toStrategist']
        toGovernance = event['toGovernance']
        toBadgerTree = event['toBadgerTree']

        table = []
        console.print("[blue]== Harvest State ==[/blue]")

        table.append(["xSushiHarvested", val(xSushiHarvested)])
        table.append(["totalxSushi", val(totalxSushi)])
        table.append(["toStrategist", val(toStrategist)])
        table.append(["toGovernance", val(toGovernance)])
        table.append(["toBadgerTree", val(toBadgerTree)])

        print(tabulate(table, headers=["account", "value"]))

    def confirm_harvest_events(self, before, after, tx):
        events = tx.events
        event = events['HarvestState'][0]

        self.printHarvestState(tx)

        xSushiHarvested = event['xSushiHarvested']
        totalxSushi = event['totalxSushi']
        toStrategist = event['toStrategist']
        toGovernance = event['toGovernance']
        toBadgerTree = event['toBadgerTree']

        assert True

    def confirm_tend(self, before, after):
        console.print("=== Compare Tend ===")
        self.manager.printCompare(before, after)

        # Increase xSushi position in strategy
        assert after.balances("xsushi", "strategy") > before.balances("xsushi", "strategy")

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities['badgerTree'] = self.manager.strategy.badgerTree()
        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

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
        return calls

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {"chef": strategy.chef(), "bar": strategy.xsushi()}
