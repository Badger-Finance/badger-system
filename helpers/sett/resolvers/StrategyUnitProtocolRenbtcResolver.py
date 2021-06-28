from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val
from tabulate import tabulate

console = Console()

class StrategyUnitProtocolRenbtcResolver(StrategyCoreResolver):

    # ===== override default =====
    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        
        strategy = self.manager.strategy

        usdp = interface.IERC20(strategy.usdp())
        usdp3crv = interface.IERC20(strategy.usdp3crv())
        
        return calls

    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)
        
        strategy = self.manager.strategy        
        unitVault = strategy.unitVault()       
        collateral = strategy.collateral()

        return calls 

    def confirm_harvest_events(self, before, after, tx):
        key = 'RenBTCStratHarvest'
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            'crvHarvested',
            'crvRecycled',
            'strategistPerformanceFee',
            'governancePerformanceFee',
            'wantDeposited',
        ]
        for key in keys:
            assert key in event

        self.printHarvestState(event, keys)
        
    def printHarvestState(self, event, keys):
        table = []
        console.print("[blue]== RenBTC Strat harvest() State ==[/blue]")
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))        
    

    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Unit Protocol RenBTC Harvest() ===")
        
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
