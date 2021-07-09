from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver
from brownie import *
from decimal import Decimal

from helpers.utils import (
    approx,
    val,
    snapSharesMatchForToken,
)
from helpers.constants import *
from helpers.multicall import Call, as_wei, func
from rich.console import Console
from tabulate import tabulate

console = Console()


class StabilizeStrategyDiggV1Resolver(StrategyCoreResolver):
    def confirm_rebalance_events(self, before, after, tx):
        key = "NoTrade"
        if key in tx.events: 
            event = tx.events[key][0]
            keys = [
                "blocknumber",
            ]
            for key in keys:
                assert key in event
            console.print("[blue]== Convex Strat rebalance() NoTrade State ==[/blue]")
            self.printState(event, keys)

        key = "TradeState"
        if key in tx.events: 
            event = tx.events[key][0]
            keys = [
                "soldAmountNormalized",
                "percentPriceChange",
                "soldPercent",
                "oldSupply",
                "newSupply",
                "diggInExpansion",
                "blocknumber",
            ]
            for key in keys:
                assert key in event
            console.print("[blue]== Convex Strat rebalance() TradeState State ==[/blue]")
            self.printState(event, keys)

        key = "Approval"
        if key in tx.events: 
            for event in tx.events[key]:
                keys = [
                    "owner",
                    "spender",
                    "value",
                ]
                for key in keys:
                    assert key in event

                console.print(
                    "[blue]== Convex Strat rebalance() Approval State ==[/blue]"
                )
                self.printState(event, keys)

            console.print(
                "[bold yellow]== Address Key ==[/bold yellow]"
            )
            console.print(
                "[yellow]SUSHISWAP_ROUTER: [/yellow]" + "[white]0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F[/white]"
            )
            console.print(
                "[yellow]UNISWAP_ROUTER: [/yellow]" + "[white]0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D[/white]"
            )

    def printState(self, event, keys):
        table = []
        nonAmounts = ["blocknumber", "soldPercent", "owner", "spender", "diggInExpansion"]
        for key in keys:
            if key in nonAmounts:
                table.append([key, event[key]])
            elif key == "soldAmountNormalized":
                table.append([key, val(event[key])])
            else:
                table.append([key, val(event[key], 9)])

        print(tabulate(table, headers=["account", "value"]))
    
    def confirm_rebalance(self, before, after, tx):
        self.confirm_rebalance_events(before, after, tx)
        console.print("=== Compare Rebalance ===")
        self.manager.printCompare(before, after)

        strategy = self.manager.strategy

        if "TradeState" in tx.events:
            event = tx.events["TradeState"][0]

            soldPercent = event["soldPercent"]
            soldAmountNormalized = event["soldAmountNormalized"]
            oldSupply = event["oldSupply"]
            newSupply = event["newSupply"]

            # Sold Digg
            if event["diggInExpansion"]:
                rebasePercentage = (newSupply - oldSupply) / oldSupply
                changedDigg = before.balances("want", "strategy") * rebasePercentage
                assert approx(
                    changedDigg * (soldPercent/100000),
                    before.balances("want", "strategy") - after.balances("want", "strategy"),
                    1,
                )
                assert approx(
                    changedDigg * (soldPercent/100000),
                    soldAmountNormalized/1e9,
                    1,
                )
                # Check that we sold some want (digg)
                assert after.balances("want", "strategy") < before.balances("want", "strategy")
                # Check that we bought some wBTC
                assert after.balances("wbtc", "strategy") > before.balances("wbtc", "strategy")

            # Sold wBTC
            else:
                assert approx(
                    before.balances("wbtc", "strategy") * (soldPercent/100000),
                    before.balances("wbtc", "strategy") - after.balances("wbtc", "strategy"),
                    1,
                )
                assert approx(
                    before.balances("wbtc", "strategy") * (soldPercent/100000),
                    soldAmountNormalized/1e8,
                    1,
                )
                # Check that we bought some want (digg)
                assert after.balances("want", "strategy") > before.balances("want", "strategy")
                # Check that we sold some wBTC
                assert after.balances("wbtc", "strategy") < before.balances("wbtc", "strategy")

        pass

    # Override: Need to adjust for Digg decimals difference
    def confirm_deposit(self, before, after, params):
        """
        Deposit Should;
        - Increase the totalSupply() of Sett tokens
        - Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        - Increase the balanceOf() want in the Sett by depositAmount
        - Decrease the balanceOf() want of the user by depositAmount
        """

        ppfs = before.get("sett.pricePerFullShare")
        console.print("=== Compare Deposit ===")
        self.manager.printCompare(before, after)

        expected_shares = Decimal(params["amount"] * (Wei("1 ether") * 1e9)) / Decimal(ppfs)
        if params.get("expected_shares") is not None:
            expected_shares = params["expected_shares"]

        # Increase the totalSupply() of Sett tokens
        assert approx(
            after.get("sett.totalSupply"),
            before.get("sett.totalSupply") + expected_shares,
            1,
        )

        # Increase the balanceOf() want in the Sett by depositAmount
        assert approx(
            after.balances("want", "sett"),
            before.balances("want", "sett") + params["amount"],
            1,
        )

        # Decrease the balanceOf() want of the user by depositAmount
        assert approx(
            after.balances("want", "user"),
            before.balances("want", "user") - params["amount"],
            1,
        )

        # Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        assert approx(
            after.balances("sett", "user"),
            before.balances("sett", "user") + expected_shares,
            1,
        )

    # Override as withdraw process works differently
    def confirm_withdraw(self, before, after, params, tx):
        """
        Withdraw Should;
        - Decrease the totalSupply() of Sett tokens
        - Decrease the balanceOf() Sett tokens for the user based on withdrawAmount and pricePerFullShare
        - Decrease the balanceOf() want in the Strategy
        - Decrease the balance() tracked for want in the Strategy
        - Decrease the available() if it is not zero
        """
        ppfs = before.get("sett.pricePerFullShare")

        console.print("=== Compare Withdraw ===")
        self.manager.printCompare(before, after)

        if params["amount"] == 0:
            assert after.get("sett.totalSupply") == before.get("sett.totalSupply")
            # Decrease the Sett tokens for the user based on withdrawAmount and pricePerFullShare
            assert after.balances("sett", "user") == before.balances("sett", "user")
            return

        # Decrease the totalSupply of Sett tokens
        assert after.get("sett.totalSupply") < before.get("sett.totalSupply")

        # Decrease the Sett tokens for the user based on withdrawAmount and pricePerFullShare
        assert after.balances("sett", "user") < before.balances("sett", "user")

        # Decrease the want in the Sett, if there was idle want
        if before.balances("want", "sett") > 0:
            assert after.balances("want", "sett") < before.balances("want", "sett")

            # Available in the sett should decrease if want decreased
            assert after.get("sett.available") <= before.get("sett.available")

        # Must review this logic:

        """ # Want in the strategy should be decreased, if idle in sett is insufficient to cover withdrawal
        if params["amount"] > before.balances("want", "sett"):
            # Adjust amount based on total balance x total supply
            # Division in python is not accurate, use Decimal package to ensure division is consistent w/ division inside of EVM
            expectedWithdraw = Decimal(
                params["amount"] * before.get("sett.balance")
            ) / Decimal(before.get("sett.totalSupply"))
            # Withdraw from idle in sett first
            expectedWithdraw -= before.balances("want", "sett")
            # First we attempt to withdraw from idle want in strategy
            if expectedWithdraw > before.balances("want", "strategy"):
                # If insufficient, we then attempt to withdraw from activities (balance of pool)
                # Just ensure that we have enough in the strategy to satisfy the request
                expectedWithdraw -= before.balances("want", "strategy")
                assert expectedWithdraw <= before.get("strategy.balanceOf") """

        # The total want between the strategy and sett should be less after than before
        # if there was previous want in strategy or sett (sometimes we withdraw entire
        # balance from the strategy pool) which we check above.
        if (
            before.balances("want", "strategy") > 0
            or before.balances("want", "sett") > 0
        ):
            assert after.balances("want", "strategy") + after.balances(
                "want", "sett"
            ) < before.balances("want", "strategy") + before.balances("want", "sett")

        # Controller rewards should earn
        if (
            before.get("strategy.withdrawalFee") > 0
            and
            # Fees are only processed when withdrawing from the strategy.
            before.balances("want", "strategy") > after.balances("want", "strategy")
        ):
            assert after.balances("want", "governanceRewards") > before.balances(
                "want", "governanceRewards"
            )

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities["sushiswap_router"] = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
        entities["uniswap_router"] = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
        entities["stabilizeVault"] = self.manager.strategy.stabilizeVault()
        entities["diggExchangeTreasury"] = self.manager.strategy.diggExchangeTreasury()

        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        diggSLP = interface.IERC20("0x9a13867048e01c663ce8Ce2fE0cDAE69Ff9F35E3")
        diggUniLP = interface.IERC20("0xE86204c4eDDd2f70eE00EAd6805f917671F56c52")
        wbtc = interface.IERC20("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599")
        digg = interface.IERC20("0x798D1bE841a82a273720CE31c822C61a67a601C3")


        calls = self.add_entity_balances_for_tokens(calls, "diggSLP", diggSLP, entities)
        calls = self.add_entity_balances_for_tokens(calls, "diggUniLP", diggUniLP, entities)
        calls = self.add_entity_balances_for_tokens(calls, "wbtc", wbtc, entities)

        return calls

    def get_strategy_destinations(self):
        return {}
