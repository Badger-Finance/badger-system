from brownie import interface
from tabulate import tabulate
from rich.console import Console

from helpers.utils import val
from .StrategyCoreResolver import StrategyCoreResolver

console = Console()


class StrategyBaseSushiResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest Basse ===")
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )

        # Sushi in badger tree should increase
        assert after.balances("xsushi", "badgerTree") >= before.balances(
            "xsushi", "badgerTree"
        )

        # Strategy should have no sushi
        assert after.balances("sushi", "strategy") == 0

        # Strategy should have no sushi in Chef

    def printHarvestState(self, event, keys):
        table = []
        console.print("[blue]== Harvest State ==[/blue]")
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))

    def confirm_harvest_events(self, before, after, tx):
        key = "HarvestState"
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            "xSushiHarvested",
            "totalxSushi",
            "toStrategist",
            "toGovernance",
            "toBadgerTree",
        ]
        for key in keys:
            assert key in event

        self.printHarvestState(event, keys)

    def confirm_tend(self, before, after, tx):
        console.print("=== Compare Tend ===")

        # Expect Increase xSushi position in strategy if we have tended sushi.
        event = tx.events["Tend"][0]
        if event["tended"] > 0:
            assert after.balances("xsushi", "strategy") > before.balances(
                "xsushi", "strategy"
            )

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities["badgerTree"] = self.manager.strategy.badgerTree()
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

    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)
        return calls

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {"chef": strategy.chef(), "bar": strategy.xsushi()}
