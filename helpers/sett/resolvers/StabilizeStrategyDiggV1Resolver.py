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

console = Console()


class StabilizeStrategyDiggV1Resolver(StrategyCoreResolver):
    def confirm_rebalance(self, before, after, tx):
        # No-op, nothing to harvest - rewards are handled externally.
        pass

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

        expected_shares = Decimal(params["amount"] * (Wei("1 ether") * 1000000000)) / Decimal(ppfs)
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

    def get_strategy_destinations(self):
        return {}
