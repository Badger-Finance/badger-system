from helpers.utils import val
from brownie import interface
from tabulate import tabulate

from helpers.multicall import Call, func, as_wei
from .StrategyCoreResolver import StrategyCoreResolver, console
from .StrategyBaseSushiResolver import StrategyBaseSushiResolver


class StrategySushiBadgerWbtcResolver(StrategyBaseSushiResolver, StrategyCoreResolver):
    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        badger = interface.IERC20(strategy.badger())

        calls = self.add_entity_balances_for_tokens(calls, "badger", badger, entities)
        return calls

    # ===== Confirmation Additions =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest Badger ===")
        self.manager.printCompare(before, after)
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Geyser should have same amount of funds

    def add_strategy_snap(self, calls, entities=None):
        strategy = self.manager.strategy
        staking_rewards_address = strategy.geyser()

        super().add_strategy_snap(calls)
        calls.append(
            Call(
                staking_rewards_address,
                [func.erc20.balanceOf, strategy.address],
                [["stakingRewards.staked", as_wei]],
            )
        )
        calls.append(
            Call(
                staking_rewards_address,
                [func.rewardPool.earned, strategy.address],
                [["stakingRewards.earned", as_wei]],
            )
        )

        return calls

    def printHarvestRewardsState(self, event, keys):
        table = []
        console.print("[blue]== Harvest Badger State ==[/blue]")
        for key in keys:
            table.append([key, val(event[key])])

        print(tabulate(table, headers=["account", "value"]))

    def confirm_harvest_events(self, before, after, tx):
        key = "HarvestBadgerState"
        assert key in tx.events
        assert len(tx.events[key]) == 1
        event = tx.events[key][0]
        keys = [
            "badgerHarvested",
            "badgerConvertedToWbtc",
            "wbtcFromConversion",
            "toGovernance",
            "toBadgerTree",
        ]
        for key in keys:
            assert key in event

        self.printHarvestRewardsState(event, keys)

    def get_strategy_destinations(self):
        destinations = super().get_strategy_destinations()
        strategy = self.manager.strategy
        destinations["stakingRewards"] = strategy.geyser()
        return destinations
