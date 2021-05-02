from brownie import interface
from helpers.multicall import Call, as_wei, func
from helpers.utils import val
from rich.console import Console
from tabulate import tabulate

from .StrategyCoreResolver import StrategyCoreResolver

console = Console()


class StrategyBasePancakeResolver(StrategyCoreResolver):
    def __init__(self, manager):
        self.manager = manager
        strategy = self.manager.strategy
        self.cakePid = strategy.cakePid()
        self.wantPid = strategy.wantPid()

    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest Basse ===")
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        assert after.get("strategy.balanceOf") >= before.get("strategy.balanceOf")

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )

    def printHarvestState(self, event, keys):
        table = []
        console.print("[blue]== Harvest State ==[/blue]")
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))

    def confirm_harvest_events(self, before, after, tx):
        key = "HarvestState"
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            "cakeHarvested",
            "cakeSold",
            "toStrategist",
            "toGovernance",
            "wantCompounded",
        ]
        for key in keys:
            assert key in event

        self.printHarvestState(event, keys)

    def confirm_tend(self, before, after, tx):
        console.print("=== Compare Tend ===")

        # Expect increase in staked Cake position in Chef if we have tended cake.
        event = tx.events["Tend"][0]
        if event["tended"] > 0:
            console.print("Tend Event", event)
            # TODO: Ensure cake balance staked in chef increases
            # console.print('Tend Results', {
            #     'before': before.get("pancakeInfo.userInfo"),
            #     'after': after.get("pancakeInfo.userInfo"),
            # })

    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        cake = interface.IERC20(strategy.cake())
        syrup = interface.IERC20(strategy.syrup())

        calls = self.add_entity_balances_for_tokens(calls, "cake", cake, entities)
        calls = self.add_entity_balances_for_tokens(calls, "syrup", syrup, entities)
        return calls

    def add_strategy_snap(self, calls, entities=None):
        strategy = self.manager.strategy
        pancake_chef_address = strategy.chef()

        super().add_strategy_snap(calls)

        if entities:
            for entityKey, entity in entities.items():
                calls.append(
                    Call(
                        pancake_chef_address,
                        [func.pancakeChef.userInfo, self.wantPid, entity],
                        [["pancakeChef.userInfo.want." + entityKey, as_wei]],
                    )
                )
                calls.append(
                    Call(
                        pancake_chef_address,
                        [func.pancakeChef.userInfo, self.cakePid, entity],
                        [["pancakeChef.userInfo.cake." + entityKey, as_wei]],
                    )
                )

        return calls

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {"chef": strategy.chef()}
