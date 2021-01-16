from tabulate import tabulate
from helpers.utils import snapBalancesMatchForToken, val
from helpers.multicall.functions import as_digg_shares
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import *
from rich.console import Console
from helpers.multicall import Call, as_wei, func
from config.badger_config import digg_decimals

console = Console()


class StrategyDiggRewardsResolver(StrategyCoreResolver):
    # ===== Strategies must implement =====
    def confirm_rebase(self, before, after, value):
        """
        All share values should stay the same.
        bDIGG values should stay the same.
        All DIGG balances should change in proportion to the rebase. (10% towards the new target)
        """
        console.print("=== Compare Rebase ===")
        self.manager.printCompare(before, after)
        # TODO: Impl more accurate rebase checks.
        if value > 10**digg_decimals:
            assert after.balances("digg", "user") > before.balances("digg", "user")
        elif value < 10**digg_decimals:
            assert after.balances("digg", "user") < before.balances("digg", "user")

    def printHarvestState(self, tx):
        events = tx.events
        event = events["HarvestState"][0]

        table = []
        console.print("[blue]== Harvest State ==[/blue]")

        table.append(["totalDigg", val(event["totalDigg"])])
        table.append(["totalShares", val(event["totalShares"])])
        table.append(["totalScaledShares", val(event["totalScaledShares"])])
        table.append(["diggIncrease", val(event["diggIncrease"])])
        table.append(["sharesIncrease", val(event["sharesIncrease"])])
        table.append(
            ["scaledSharesIncrease", val(event["scaledSharesIncrease"])]
        )

        print(tabulate(table, headers=["account", "value"]))

    def confirm_harvest(self, before, after, tx):
        strategy = self.manager.strategy
        digg = interface.IDigg(strategy.want())
        # rewards = interface.IDiggRewardsFaucet(strategy.geyser())
        super().confirm_harvest(before, after, tx)

        # table = []
        # table.append(["sett.keeper", self.sett.keeper()])
        # print(tabulate(table, headers=["account", "value"]))
        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert (
            after.get("strategy.balanceOf") >= before_balance if before_balance else 0
        )

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )

    def add_balances_snap(self, calls, entities):
        want = self.manager.want
        sett = self.manager.sett

        # Add FARM token balances.
        digg = interface.IERC20(self.manager.strategy.want())

        calls = self.add_entity_balances_for_tokens(calls, "digg", digg, entities)
        calls = self.add_entity_shares_for_tokens(calls, "digg", digg, entities)
        calls = self.add_entity_balances_for_tokens(calls, "sett", sett, entities)


        return calls

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "diggFaucet": strategy.diggFaucet(),
        }

    def add_strategy_snap(self, calls):
        super().add_strategy_snap(calls)

        sett = self.manager.sett
        strategy = self.manager.strategy

        calls.append(
            Call(
                strategy.diggFaucet(),
                [func.diggFaucet.earned],
                [["diggFaucet.earned", as_wei]],
            )
        )

        # Sett Shares
        calls.append(Call(sett.address, [func.sett.shares], [["sett.shares", as_wei]],))

        # Strategy Shares
        calls.append(
            Call(
                strategy.address,
                [func.strategy.sharesOf],
                [["strategy.sharesOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.sharesOfPool],
                [["strategy.sharesOfPool", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.sharesOfWant],
                [["strategy.sharesOfWant", as_wei]],
            )
        )

        return calls
