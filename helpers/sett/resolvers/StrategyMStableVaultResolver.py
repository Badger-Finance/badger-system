from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val
from tabulate import tabulate

console = Console()


class StrategyMStableVaultResolver(StrategyCoreResolver):

    # ===== override default =====
    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)

        strategy = self.manager.strategy        
        mstableVault = strategy.vault()       

        return calls 

    def confirm_harvest_events(self, before, after, tx):
        key = 'MStableHarvest'
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            'mtaTotal',
            'mtaSentToVoterProxy',
            'mtaRecycledToWant',
            'lpComponentPurchased',
            'wantProcessed',
            'wantFees',
            'wantDeposited',
            'mtaPostVesting',
            'mtaFees',
            'mtaPostVestingSentToBadgerTree'
        ]
        for key in keys:
            assert key in event

        print(event)

        self.printMStableState(event, keys)

    def printMStableState(self, event, keys):
        table = []
        console.print("[blue]== MStable Strat harvest() State ==[/blue]")
        for key in keys:
            if isinstance(event[key], tuple):
                for index, item in enumerate(event[key]):
                    table.append([key + " " + str(index), val(event[key][index])])
            else:
                table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))        


    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare MStable Harvest() ===")

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
        assert True

    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """

        strategy = self.manager.strategy
        return {}