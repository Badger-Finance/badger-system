from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import *
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from helpers.utils import val, approx
from tabulate import tabulate
from helpers.registry import registry

console = Console()


class StrategyConvexStakingOptimizerResolver(StrategyCoreResolver):

    # ===== override default =====
    def confirm_harvest_events(self, before, after, tx):
        key = "TreeDistribution"
        assert key in tx.events
        assert len(tx.events[key]) >= 1
        for event in tx.events[key]:
            keys = [
                "token",
                "amount",
                "blockNumber",
                "timestamp",
            ]
            for key in keys:
                assert key in event

            console.print(
                "[blue]== Convex Strat harvest() TreeDistribution State ==[/blue]"
            )
            self.printState(event, keys)

        key = "PerformanceFeeGovernance"
        assert key in tx.events
        assert len(tx.events[key]) >= 1
        for event in tx.events[key]:
            keys = [
                "destination",
                "token",
                "amount",
                "blockNumber",
                "timestamp",
            ]
            for key in keys:
                assert key in event

            console.print(
                "[blue]== Convex Strat harvest() PerformanceFeeGovernance State ==[/blue]"
            )
            self.printState(event, keys)

        key = "PerformanceFeeStrategist"
        assert key not in tx.events
        # Strategist performance fee is set to 0

    def confirm_tend_events(self, before, after, tx):
        key = "Tend"
        assert key in tx.events
        assert len(tx.events[key]) == 1

        event = tx.events[key][0]
        keys = [
            "tended",
        ]
        for key in keys:
            assert key in event

        console.print("[blue]== Convex Strat tend() State ==[/blue]")
        self.printState(event, keys)

        key = "TendState"
        assert key in tx.events
        assert len(tx.events[key]) == 1

        event = tx.events[key][0]
        keys = [
            "crvTended",
            "cvxTended",
            "cvxCrvTended",
        ]
        for key in keys:
            assert key in event
        self.printState(event, keys)

    def printState(self, event, keys):
        table = []
        nonAmounts = ["token", "destination", "blockNumber", "timestamp"]
        for key in keys:
            if key in nonAmounts:
                table.append([key, event[key]])
            else:
                table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))

    # ===== Strategies must implement =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Convex Harvest() ===")

        # Harvest event emission not yet implemented
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )
        # 80% of collected cvx is deposited on helper vaults
        assert approx(
            (
                after.balances("cvx", "cvxHelperVault")
                - before.balances("cvx", "cvxHelperVault")
            ),
            abs(
                before.balances("cvx", "cvxRewardsPool")
                - after.balances("cvx", "cvxRewardsPool")
            )
            * 0.8,
            1,
        )
        # 80% of collected cvxCrv is deposited on helper vaults
        assert approx(
            (
                after.balances("cvxCrv", "cvxCrvHelperVault")
                - before.balances("cvxCrv", "cvxCrvHelperVault")
            ),
            abs(
                before.balances("cvxCrv", "cvxCrvRewardsPool")
                - after.balances("cvxCrv", "cvxCrvRewardsPool")
            )
            * 0.8,
            1,
        )
        # Check that helper vault shares were distributed correctly:
        cvxHelperVault = SettV4.at(registry.convex.cvxHelperVault)
        cvxCrvHelperVault = SettV4.at(registry.convex.cvxCrvHelperVault)

        # 80% of cvxHelperVault shares were distributed through the tree
        assert approx(
            (
                after.balances("cvx", "cvxHelperVault")
                - before.balances("cvx", "cvxHelperVault")
            )
            * (cvxHelperVault.getPricePerFullShare() / 1e18)
            * 0.8,
            after.balances("bCvx", "badgerTree")
            - before.balances("bCvx", "badgerTree"),
            1,
        )
        # 20% of cvxHelperVault shares were distributed through the tree
        assert approx(
            (
                after.balances("cvx", "cvxHelperVault")
                - before.balances("cvx", "cvxHelperVault")
            )
            * (cvxHelperVault.getPricePerFullShare() / 1e18)
            * 0.2,
            after.balances("bCvx", "governanceRewards")
            - before.balances("bCvx", "governanceRewards"),
            1,
        )
        # 80% of cvxCrvHelperVault shares were distributed through the tree
        assert approx(
            (
                after.balances("cvxCrv", "cvxCrvHelperVault")
                - before.balances("cvxCrv", "cvxCrvHelperVault")
            )
            * (cvxCrvHelperVault.getPricePerFullShare() / 1e18)
            * 0.8,
            after.balances("bCvxCrv", "badgerTree")
            - before.balances("bCvxCrv", "badgerTree"),
            1,
        )
        # 20% of cvxCrvHelperVault shares were distributed through the tree
        assert approx(
            (
                after.balances("cvxCrv", "cvxCrvHelperVault")
                - before.balances("cvxCrv", "cvxCrvHelperVault")
            )
            * (cvxCrvHelperVault.getPricePerFullShare() / 1e18)
            * 0.2,
            after.balances("bCvxCrv", "governanceRewards")
            - before.balances("bCvxCrv", "governanceRewards"),
            1,
        )

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
        entities["cvxHelperVault"] = registry.convex.cvxHelperVault
        entities["cvxCrvHelperVault"] = registry.convex.cvxCrvHelperVault

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
        bCvx = interface.IERC20(registry.convex.cvxHelperVault)
        bCvxCrv = interface.IERC20(registry.convex.cvxCrvHelperVault)

        calls = self.add_entity_balances_for_tokens(calls, "crv", crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvx", cvx, entities)
        calls = self.add_entity_balances_for_tokens(calls, "3Crv", _3Crv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "BOR", BOR, entities)
        calls = self.add_entity_balances_for_tokens(calls, "PNT", PNT, entities)
        calls = self.add_entity_balances_for_tokens(calls, "WBTC", wbtc, entities)
        calls = self.add_entity_balances_for_tokens(calls, "USDC", usdc, entities)
        calls = self.add_entity_balances_for_tokens(calls, "cvxCrv", cvxCrv, entities)
        calls = self.add_entity_balances_for_tokens(calls, "bCvx", bCvx, entities)
        calls = self.add_entity_balances_for_tokens(calls, "bCvxCrv", bCvxCrv, entities)

        return calls
