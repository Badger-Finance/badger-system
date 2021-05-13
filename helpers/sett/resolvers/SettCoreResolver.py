from brownie import *
from helpers.constants import *
from helpers.multicall import Call, as_wei, func
from rich.console import Console

console = Console()


class SettCoreResolver:
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
        sett = self.manager.sett

        calls = self.add_entity_balances_for_tokens(calls, "sett", sett, entities)
        return calls

    def add_sett_snap(self, calls):
        sett = self.manager.sett

        # Global Numbers
        # calls.append(
        #     Call(sett.address, [func.sett.balance], [["sett.balance", as_wei]])
        # )
        # calls.append(
        #     Call(sett.address, [func.sett.available], [["sett.available", as_wei]])
        # )
        # calls.append(
        #     Call(
        #         sett.address,
        #         [func.sett.getPricePerFullShare],
        #         [["sett.pricePerFullShare", as_wei]],
        #     )
        # )
        # calls.append(
        #     Call(sett.address, [func.erc20.totalSupply], [["sett.totalSupply", as_wei]])
        # )

        # calls.append(Call(sett.address, [func.sett.min], [["sett.min"]]))
        # calls.append(Call(sett.address, [func.sett.max], [["sett.max"]]))

        # ERC20
        # calls.append(Call(sett.address, [func.erc20.name], [["sett.name"]]))
        # calls.append(Call(sett.address, [func.erc20.symbol], [["sett.symbol"]]))
        # calls.append(Call(sett.address, [func.erc20.decimals], [["sett.decimals"]]))

        # Permissioned Accounts
        # calls.append(Call(sett.address, [func.sett.controller], [["sett.controller"]]))
        # calls.append(Call(sett.address, [func.sett.governance], [["sett.governance"]]))
        # calls.append(Call(sett.address, [func.sett.strategist], [["sett.strategist"]]))
        # calls.append(Call(sett.address, [func.sett.keeper], [["sett.keeper"]]))
        # calls.append(Call(sett.address, [func.sett.token], [["sett.token"]]))

        return calls

    # ===== Verify strategy action results =====

    def confirm_values(self, before, after, params):
        """
        Every value should be the same
        Just print out a DIFF report
        Did a users' balance change?
        Did any of the variables change?
        Print out storage layout of the contract
        """
