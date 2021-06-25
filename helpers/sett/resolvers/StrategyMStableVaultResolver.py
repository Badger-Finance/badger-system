from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from config.badger_config import sett_config
from brownie import interface
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val, approx
from tabulate import tabulate
from helpers.registry import registries

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

        self.printMStableState(event, keys)

        assert approx(
            float(event['mtaSentToVoterProxy']),
            float(event['mtaTotal']) * sett_config.native.imBtc.params.govMta/10000,
            1,
        )

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

    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """

        strategy = self.manager.strategy
        return {} 

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities["badgerTree"] = self.manager.strategy.badgerTree()
        entities["strategy"] = self.manager.strategy.address
        entities["voterProxy"] = self.manager.strategy.voterProxy()
        entities["mStableVault"] = self.manager.strategy.vault()


        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        registry = registries.get_registry("eth")
        mstable = registry.mstable

        mta = interface.IERC20(strategy.mta())
        weth = interface.IERC20(strategy.weth())
        mBTC = interface.IERC20(strategy.mBTC())
        wbtc = interface.IERC20(registry.tokens.wbtc)

        calls = self.add_entity_balances_for_tokens(calls, "mta", mta, entities)
        calls = self.add_entity_balances_for_tokens(calls, "weth", weth, entities)
        calls = self.add_entity_balances_for_tokens(calls, "mBTC", mBTC, entities)
        calls = self.add_entity_balances_for_tokens(calls, "wbtc", wbtc, entities)

        return calls

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