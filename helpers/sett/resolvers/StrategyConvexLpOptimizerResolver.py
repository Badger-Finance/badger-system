from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import interface, accounts
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
            'sushiTended',
            'crvTended',
            'cvxTended',
            'cvxEthLpTended',
            'cvxCrvCrvLpTended'
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
        self.manager.printCompare(before, after)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def confirm_tend(self, before, after, tx):
        self.confirm_tend_events(before, after, tx)

        console.print("=== Compare Convex Tend() ===")
        self.manager.printCompare(before, after)

        # Expect Increase xSushi position in strategy if we have tended sushi.
        event = tx.events["Tend"][0]
        if event["tended"] > 0:
            assert after.balances("xsushi", "strategy") > before.balances(
                "xsushi", "strategy"
            )

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
        #entities["user"] = accounts[0].address # deployer being used as user on test_strategy_flow.py
        entities["randomUser"] = accounts[6].address
        entities["convexMasterChef"] = self.manager.strategy.convexMasterChef()


        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        xsushi = interface.IERC20(strategy.xsushi())
        crv = interface.IERC20(strategy.crv())
        cvx = interface.IERC20(strategy.cvx())
        cvxCrv = interface.IERC20(strategy.cvxCrv())
        cvxCRV_CRV_SLP = interface.IERC20(strategy.cvxCRV_CRV_SLP())
        CVX_ETH_SLP = interface.IERC20(strategy.CVX_ETH_SLP())

        calls = self.add_entity_balances_for_tokens(calls, "xsushi", xsushi, entities)
        calls = self.add_entity_balances_for_tokens(calls, "crv", crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvx", cvx, entities)
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

    