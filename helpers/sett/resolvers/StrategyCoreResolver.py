from brownie import *
from decimal import Decimal
from rich.console import Console

from helpers.utils import approx, val
from helpers.constants import *
from helpers.multicall import Call, as_wei, func
from scripts.systems.constants import SettType

console = Console()

class StrategyCoreResolver:
    def __init__(self, manager):
        self.manager = manager

    # ===== Read strategy data =====

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        for entityKey, entity in entities.items():
            calls.append(
                Call(
                    token.address,
                    [func.erc20.balanceOf, entity],
                    [["balances." + tokenKey + "." + entityKey, as_wei]],
                )
            )

        return calls

    def add_balances_snap(self, calls, entities):
        want = self.manager.want
        sett = self.manager.sett

        calls = self.add_entity_balances_for_tokens(calls, "want", want, entities)
        calls = self.add_entity_balances_for_tokens(calls, "sett", sett, entities)
        return calls

    def add_sett_snap(self, calls):
        sett = self.manager.sett

        calls.append(
            Call(sett.address, [func.sett.balance], [["sett.balance", as_wei]])
        )
        calls.append(
            Call(sett.address, [func.sett.available], [["sett.available", as_wei]])
        )
        calls.append(
            Call(
                sett.address, [func.sett.getPricePerFullShare], [["sett.pricePerFullShare", as_wei]]
            )
        )
        calls.append(
            Call(sett.address, [func.erc20.totalSupply], [["sett.totalSupply", as_wei]])
        )

        return calls

    def add_strategy_snap(self, calls):
        strategy = self.manager.strategy

        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOfPool],
                [["strategy.balanceOfPool", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOfWant],
                [["strategy.balanceOfWant", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.balanceOf],
                [["strategy.balanceOf", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.withdrawalFee],
                [["strategy.withdrawalFee", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.performanceFeeGovernance],
                [["strategy.performanceFeeGovernance", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.address,
                [func.strategy.performanceFeeStrategist],
                [["strategy.performanceFeeStrategist", as_wei]],
            )
        )

        return calls

    # ===== Verify strategy action results =====

    def confirm_earn(self, before, after, params):
        """
        Earn Should:
        - Decrease the balanceOf() want in the Sett
        - Increase the balanceOf() want in the Strategy
        - Increase the balanceOfPool() in the Strategy
        - Reduce the balanceOfWant() in the Strategy to zero
        - Users balanceOf() want should not change
        """

        console.print("=== Compare Earn ===")
        self.manager.printCompare(before, after)

        assert after.balances("want", "sett") <= before.balances("want", "sett")
        assert after.get("strategy.balanceOf") > before.get("strategy.balanceOf")
        assert after.balances("want", "user") == before.balances("want", "user")

        if params.get("sett_type") == SettType.DIGG:
            deposited = before.balances("want", "sett") - after.balances("want", "sett")
            assert after.get("strategy.balanceOfWant") == deposited
            assert (after.get("strategy.balanceOfPool") == 0 or  # Basic digg rewards strategy has no position.
                after.get("strategy.balanceOfPool") > before.get("strategy.balanceOfPool"))
        else:
            assert after.get("strategy.balanceOfWant") == 0
            assert after.get("strategy.balanceOfPool") > before.get(
                "strategy.balanceOfPool"
            )

    def confirm_withdraw(self, before, after, params):
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

        # Decrease the totalSupply of Sett tokens
        assert after.get("sett.totalSupply") < before.get("sett.totalSupply")

        # Decrease the Sett tokens for the user based on withdrawAmount and pricePerFullShare
        assert after.balances("sett", "user") < before.balances("sett", "user")

        # Decrease the want in the Sett, if there was idle want
        if before.balances("want", "sett") > 0:
            assert after.balances("want", "sett") < before.balances("want", "sett")

            # Available in the sett should decrease if want decreased
            assert after.get("sett.available") <= before.get("sett.available")

        # Want in the strategy should be decreased, if idle in sett is insufficient to cover withdrawal
        if params["amount"] > before.balances("want", "sett"):
            # Adjust amount based on total balance x total supply
            # Division in python is not accurate, use Decimal package to ensure division is consistent w/ division inside of EVM
            if params.get("sett_type") == SettType.DIGG:
                expectedWithdraw = Decimal(params["shares"] * before.get("sett.balance")) / Decimal(before.get("sett.totalSupply"))
            else:
                expectedWithdraw = Decimal(params["amount"] * before.get("sett.balance")) / Decimal(before.get("sett.totalSupply"))
            # Withdraw from idle in sett first
            expectedWithdraw -= before.balances("want", "sett")
            # First we attempt to withdraw from idle want in strategy
            if expectedWithdraw > before.balances("want", "strategy"):
                # If insufficient, we then attempt to withdraw from activities (balance of pool)
                # Just ensure that we have enough in the pool balance to satisfy the request
                assert expectedWithdraw - before.balances("want", "strategy") <= before.get("strategy.balanceOfPool")
            ''' TODO: Tests failing here. Balance of strategy did not change.
            (Pdb) before.get("strategy.balanceOf")
            2280000000000
            (Pdb) after.get("strategy.balanceOf")
            2280000000000
            (Pdb) expectedWithdraw
            Decimal('1080000000000')
            '''
            assert approx(
                before.get("strategy.balanceOf"),
                after.get("strategy.balanceOf") + expectedWithdraw,
                1,
            )

        # The total want between the strategy and sett should be less after than before
        assert after.get("strategy.balanceOf") + after.balances(
            "want", "sett"
        ) < before.get("strategy.balanceOf") + before.balances("want", "sett")

        # Controller rewards should earn
        self.manager.printCompare(before, after)
        if before.get("strategy.withdrawalFee") > 0:
            assert after.balances("want", "governanceRewards") > before.balances(
                "want", "governanceRewards"
            )

    def confirm_deposit(self, before, after, params):
        """
        Deposit Should;
        - Increase the totalSupply() of Sett tokens
        - Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        - Increase the balanceOf() want in the Sett by depositAmountt
        - Decrease the balanceOf() want of the user by depositAmountt
        """

        ppfs = before.get("sett.pricePerFullShare")
        console.print("=== Compare Deposit ===")
        self.manager.printCompare(before, after)

        expected_shares = Decimal(params["amount"] * Wei("1 ether")) / Decimal(ppfs)
        # For sett type DIGG, bDIGG is minted 1:1 w/ digg shares (not fragments).
        # DIGG balances are represented as fragments.
        if params.get("sett_type") == SettType.DIGG:
            expected_shares = Decimal(params.get("shares") * Wei("1 ether")) / Decimal(ppfs)

        # Increase the totalSupply() of Sett tokens
        assert approx(after.get("sett.totalSupply"), before.get("sett.totalSupply") + expected_shares, 1)

        # Increase the balanceOf() want in the Sett by depositAmount
        assert approx(after.balances("want", "sett"), before.balances("want", "sett") + params["amount"], 1)

        # Decrease the balanceOf() want of the user by depositAmount
        assert approx(after.balances("want", "user"), before.balances("want", "user") - params["amount"], 1)

        # Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        assert approx(after.balances("sett", "user"), before.balances("sett", "user") + expected_shares, 1)

    # ===== Strategies must implement =====

    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest ===")
        self.manager.printCompare(before, after)
        valueGained = after.get("sett.pricePerFullShare") > before.get("sett.pricePerFullShare")

        # # Strategist should earn if fee is enabled and value was generated
        # if before.get("strategy.performanceFeeStrategist") > 0 and valueGained:
        #     assert after.balances("want", "strategist") > before.balances(
        #         "want", "strategist"
        #     )

        # # Strategist should earn if fee is enabled and value was generated
        # if before.get("strategy.performanceFeeGovernance") > 0 and valueGained:
        #     assert after.balances("want", "governanceRewards") > before.balances(
        #         "want", "governanceRewards"
        #     )

    def confirm_tend(self, before, after):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero

        (Strategy Must Implement)
        """
        assert False

    def get_strategy_destinations():
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """
        assert False
