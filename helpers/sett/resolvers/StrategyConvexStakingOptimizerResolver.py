from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface, accounts
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val
from tabulate import tabulate

console = Console()

class StrategyConvexStakingOptimizerResolver(StrategyCoreResolver):

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

        console.print("[blue]== Convex Strat harvest() State ==[/blue]")
        self.printState(event, keys)

    def confirm_tend_events(self, before, after, tx):
        key = 'Tend'
        assert key in tx.events
        assert len(tx.events[key]) == 1

        event = tx.events[key][0]
        keys = [
            'tended',
        ]
        for key in keys:
            assert key in event

        console.print("[blue]== Convex Strat tend() State ==[/blue]")
        self.printState(event, keys)

        key = 'TendState'
        assert key in tx.events
        assert len(tx.events[key]) == 1

        event = tx.events[key][0]
        keys = [
            'crvTended',
            'cvxTended',
            'cvxCrvTended',
        ]
        for key in keys:
            assert key in event
        self.printState(event, keys)

    def printState(self, event, keys):
        table = []
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))       

    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Convex Harvest() ===")

        # Harvest event emission not yet implemented
        # self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def confirm_tend(self, before, after, tx):
        self.confirm_tend_events(before, after, tx)

        console.print("=== Compare Convex Tend() ===")
        self.manager.printCompare(before, after)

        # Expect decrease crv balance of rewardsPool and increase cvx cvxCrv
        event = tx.events["TendState"][0]
        if event["cvxTended"] > 0:
            assert after.balances("cvx", "cvxRewardsPool") > before.balances(
                "cvx", "cvxRewardsPool"
            )
            assert after.balances("cvx", "strategy") == before.balances(
                "cvx", "strategy"
            )
            assert before.balances("cvx", "strategy") == 0

        if event["cvxCrvTended"] > 0:
            assert after.balances("cvxCrv", "cvxCrvRewardsPool") > before.balances(
                "cvxCrv", "cvxCrvRewardsPool"
            )
            assert after.balances("cvxCrv", "strategy") == before.balances(
                "cvxCrv", "strategy"
            )
            assert before.balances("cvxCrv", "strategy") == 0

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
        entities["convexMasterChef"] = self.manager.strategy.convexMasterChef()
        entities["cvxCrvRewardsPool"] = self.manager.strategy.cvxCrvRewardsPool()
        entities["cvxRewardsPool"] = self.manager.strategy.cvxRewardsPool()
        entities["baseRewardsPool"] = self.manager.strategy.baseRewardsPool()


        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        crv = interface.IERC20(strategy.crv())
        cvx = interface.IERC20(strategy.cvx())
        _3Crv = interface.IERC20("0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490") 
        BOR = interface.IERC20("0x3c9d6c1c73b31c837832c72e04d3152f051fc1a9") 
        PNT = interface.IERC20("0x89ab32156e46f46d02ade3fecbe5fc4243b9aaed") 
        wbtc = interface.IERC20("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599")
        usdc = interface.IERC20("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
        cvxCrv = interface.IERC20(strategy.cvxCrv())
        cvxCRV_CRV_SLP = interface.IERC20(strategy.cvxCRV_CRV_SLP())
        CVX_ETH_SLP = interface.IERC20(strategy.CVX_ETH_SLP())

        calls = self.add_entity_balances_for_tokens(calls, "crv", crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvx", cvx, entities)
        calls = self.add_entity_balances_for_tokens(calls, "3Crv", _3Crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "BOR", BOR, entities)
        calls = self.add_entity_balances_for_tokens(calls, "PNT", PNT, entities)
        calls = self.add_entity_balances_for_tokens(calls, "WBTC", wbtc, entities)
        calls = self.add_entity_balances_for_tokens(calls, "USDC", usdc, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvxCrv", cvxCrv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvxCRV_CRV_SLP", cvxCRV_CRV_SLP, entities)
        calls = self.add_entity_balances_for_tokens(calls, "CVX_ETH_SLP", CVX_ETH_SLP, entities)

        return calls

    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)

        strategy = self.manager.strategy
    
        cvxCRV_CRV_SLP_Pid = strategy.cvxCRV_CRV_SLP_Pid()
        CVX_ETH_SLP_Pid = strategy.CVX_ETH_SLP_Pid()

        convexMasterChef = strategy.convexMasterChef()

        if entities:
            for entityKey, entity in entities.items():
                calls.append(
                    Call(
                        convexMasterChef,
                        [func.sushiChef.userInfo, cvxCRV_CRV_SLP_Pid, entity],
                        [["convexMasterChef.userInfo.cvxCRV_CRV_SLP_Pid." + entityKey, as_wei]],
                    )
                )
                calls.append(
                    Call(
                        convexMasterChef,
                        [func.sushiChef.userInfo, CVX_ETH_SLP_Pid, entity],
                        [["convexMasterChef.userInfo.CVX_ETH_SLP_Pid." + entityKey, as_wei]],
                    )
                )

        return calls

    