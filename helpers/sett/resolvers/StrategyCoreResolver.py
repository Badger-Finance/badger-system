from brownie import *
from helpers.constants import *
from helpers.multicall import Call, as_wei, func


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
                sett.address, [func.sett.getPricePerFullShare], [["sett.ppfs", as_wei]]
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

        assert after.balances("want", "sett") <= before.balances("want", "sett")
        assert after.get("strategy.balanceOfWant") == 0
        assert after.get("strategy.balanceOfPool") > before.get(
            "strategy.balanceOfPool"
        )
        assert after.get("strategy.balanceOf") > before.get("strategy.balanceOf")
        assert after.balances("want", "user") == before.balances("want", "user")

    def confirm_withdraw(self, before, after, params):
        """
        Withdraw Should;
        - Decrease the totalSupply() of Sett tokens
        - Decrease the balanceOf() Sett tokens for the user based on withdrawAmount and pricePerFullShare
        - Decrease the balanceOf() want in the Strategy
        - Decrease the balance() tracked for want in the Strategy
        - Decrease the available() if it is not zero
        """
        assert after.get("sett.totalSupply") < before.get("sett.totalSupply")
        assert after.balances("sett", "user") < before.balances("sett", "user")
        assert after.balances("want", "sett") <= before.balances("want", "sett")
        assert after.get("sett.available") <= before.get("sett.available")
        assert after.get("strategy.balanceOfPool") <= before.get(
            "strategy.balanceOfPool"
        )
        assert after.get("strategy.balanceOfWant") <= before.get(
            "strategy.balanceOfWant"
        )

        assert after.get("strategy.balanceOf") + after.balances(
            "want", "sett"
        ) < before.get("strategy.balanceOf") + before.balances("want", "sett")

        # Controller rewards should earn
        # if before.get("strategy.withdrawalFee") > 0:
        #     assert after.balances("want", "governanceRewards") > before.balances(
        #         "want", "governanceRewards"
        #     )

    def confirm_deposit(self, before, after, params):
        """
        Deposit Should;
        - Increase the totalSupply() of Sett tokens
        - Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        - Increase the balanceOf() want in the Sett by depositAmountt
        - Decrease the balanceOf() want of the user by depositAmountt
        """

        # Increase the totalSupply() of Sett tokens
        assert (
            after.get("sett.totalSupply")
            == before.get("sett.totalSupply") + params["amount"]
        )

        print(after)

        # Increase the balanceOf() want in the Sett by depositAmount
        assert (
            after.balances("want", "sett")
            == before.balances("want", "sett") + params["amount"]
        )

        # Decrease the balanceOf() want of the user by depositAmount
        assert (
            after.balances("want", "user")
            == before.balances("want", "user") - params["amount"]
        )

        # Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
        assert after.balances("sett", "user") > before.balances("sett", "user")

    # ===== Strategies must implement =====

    def confirm_harvest(self, before, after):
        # Strategist should earn if fee is enabled and value was generated
        if before.get("strategy.performanceFeeStrategist") > 0 and after.get(
            "sett.pricePerFullShare"
        ) > before.get("sett.pricePerFullShare"):
            assert after.balances("want", "strategist") > before.balances(
                "want", "strategist"
            )

        # Strategist should earn if fee is enabled and value was generated
        if before.get("strategy.performanceFeeGovernance") > 0 and after.get(
            "sett.pricePerFullShare"
        ) > before.get("sett.pricePerFullShare"):
            assert after.balances("want", "governance") > before.balances(
                "want", "governance"
            )

    def confirm_tend(self, before, after):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero
        """
        assert False

    def get_strategy_destinations():
        assert False
