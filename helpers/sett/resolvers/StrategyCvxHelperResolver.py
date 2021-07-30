from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface, accounts
from rich.console import Console
from helpers.utils import val
from tabulate import tabulate

console = Console()


class StrategyCvxHelperResolver(StrategyCoreResolver):

    # ===== override default =====
    def confirm_harvest_events(self, before, after, tx):
        key = "Tend"
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            "tended",
        ]
        for key in keys:
            assert key in event

        console.print("[blue]== Cvx Helper Strat harvest() State ==[/blue]")
        self.printState(event, keys)

    def printState(self, event, keys):
        table = []
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))

    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Cvx Helper Harvest() ===")

        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)
        self.manager.printCompare(before, after)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )

    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """

        strategy = self.manager.strategy
        return {}

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities["strategy"] = self.manager.strategy.address
        entities["cvxRewardsPool"] = self.manager.strategy.cvxRewardsPool()

        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        crv = interface.IERC20(strategy.crv())
        cvx = interface.IERC20(strategy.cvx())
        threeCrv = interface.IERC20(strategy.threeCrv())
        cvxCrv = interface.IERC20(strategy.cvxCrv())
        usdc = interface.IERC20(strategy.usdc())

        calls = self.add_entity_balances_for_tokens(calls, "crv", crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvx", cvx, entities)
        calls = self.add_entity_balances_for_tokens(calls, "3Crv", threeCrv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvxCrv", cvxCrv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "usdc", usdc, entities)

        return calls
