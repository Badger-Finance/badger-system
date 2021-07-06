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
        console.print("=== Compare Rebalance ===")
        self.manager.printCompare(before, after)
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


        calls = self.add_entity_balances_for_tokens(calls, "diggSLP", diggSLP, entities)
        calls = self.add_entity_balances_for_tokens(calls, "diggUniLP", diggUniLP, entities)
        calls = self.add_entity_balances_for_tokens(calls, "wbtc", wbtc, entities)

        return calls

    def get_strategy_destinations(self):
        return {}
