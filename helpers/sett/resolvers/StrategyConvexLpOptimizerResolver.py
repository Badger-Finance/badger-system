from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val
from tabulate import tabulate

console = Console()

class StrategyConvexLpOptimizerResolver(StrategyCoreResolver):

    # ===== override default =====
    def confirm_harvest_events(self, before, after, tx):
        key = 'HarvestState'
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            'xSushiHarvested',
            'totalxSushi',
            'toStrategist',
            'toGovernance',
            'toBadgerTree',
            'timestamp',
            'blockNumber',
        ]
        for key in keys:
            assert key in event

        print(event)

        console.print("[blue]== Convex Strat harvest() State ==[/blue]")
        self.printState(event, keys)

    def confirm_tend_events(self, before, after, tx):
        key = 'Tend'
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            'sushiTended',
        ]
        for key in keys:
            assert key in event

        print(event)

        console.print("[blue]== Convex Strat tend() State ==[/blue]")
        self.printState(event, keys)

    def printState(self, event, keys):
        table = []
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))       

    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Convex Harvest() ===")

        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def confirm_tend(self, before, after, tx):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero
        (Strategy Must Implement)
        """
        console.print("=== Compare Convex tend() ===")

        self.confirm_tend_events(before, after, tx)

        super().confirm_tend(before, after, tx)

    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """

        strategy = self.manager.strategy
        return {} 

    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)

        strategy = self.manager.strategy

        calls.append(
            Call(
                strategy.xsushi(),
                [func.erc20.balanceOf, strategy.address],
                [["xsushi.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.crv(),
                [func.erc20.balanceOf, strategy.address],
                [["crv.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.cvx(),
                [func.erc20.balanceOf, strategy.address],
                [["cvx.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.cvxCrv(),
                [func.erc20.balanceOf, strategy.address],
                [["cvxCrv.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.cvxCRV_CRV_SLP(),
                [func.erc20.balanceOf, strategy.address],
                [["cvxCRV_CRV_SLP.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.CVX_ETH_SLP(),
                [func.erc20.balanceOf, strategy.address],
                [["CVX_ETH_SLP.balanceOf", as_wei]],
            )
        )

        return calls 
    