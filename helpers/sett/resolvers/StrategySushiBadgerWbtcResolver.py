from helpers.utils import val
from brownie import *
from tabulate import tabulate

from helpers.constants import *
from helpers.multicall import Call, func, as_wei
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver, console

def confirm_harvest_badger_lp(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle BADGER to zero
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf >= before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


class StrategySushiBadgerWbtcResolver(StrategyCoreResolver):

    # ===== Snapshot Additions =====
    def add_entity_balances_for_tokens(self, calls, tokenKey, token, entities):
        entities['badgerTree'] = self.manager.strategy.badgerTree()
        super().add_entity_balances_for_tokens(calls, tokenKey, token, entities)
        return calls

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy
        
        badger = interface.IERC20(strategy.badger())
        sushi = interface.IERC20(strategy.sushi())
        xsushi = interface.IERC20(strategy.xsushi())

        calls = self.add_entity_balances_for_tokens(calls, "badger", badger, entities)
        calls = self.add_entity_balances_for_tokens(calls, "sushi", sushi, entities)
        calls = self.add_entity_balances_for_tokens(calls, "xsushi", xsushi, entities)
        return calls
    
    # ===== Confirmation Additions =====
    def confirm_harvest(self, before, after, tx):
        console.print("=== Compare Harvest ===")
        self.manager.printCompare(before, after)
        self.confirm_harvest_events(before, after, tx)

        super().confirm_harvest(before, after, tx)

        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert after.get("strategy.balanceOf") >= before_balance if before_balance else 0

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

        # Sushi in badger tree should increase
        assert after.balances("xsushi", "badgerTree") > before.balances("xsushi", "badgerTree")

        # Strategy should have no sushi
        assert after.balances("sushi", "strategy") == 0

        # Geyser should have same amount of funds

    def add_strategy_snap(self, calls):
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
        return calls
    
    def confirm_tend(self, before, after):
        console.print("=== Compare Tend ===")
        self.manager.printCompare(before, after)

        # Increase xSushi position in strategy
        assert after.balances("xsushi", "strategy") > before.balances("xsushi", "strategy")

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "chef": strategy.chef(),
            "bar": strategy.xsushi(),
            "stakingRewards": strategy.geyser(),
        }

    # ===== Confirmation Helpers =====
    def printHarvestState(self, tx):

        events = tx.events
        event = events['HarvestState'][0]

        xSushiHarvested = event['xSushiHarvested']
        totalxSushi = event['totalxSushi']
        toStrategist = event['toStrategist']
        toGovernance = event['toGovernance']
        toBadgerTree = event['toBadgerTree']

        table = []
        console.print("[blue]== Harvest State ==[/blue]")

        table.append(["xSushiHarvested", val(xSushiHarvested)])
        table.append(["totalxSushi", val(totalxSushi)])
        table.append(["toStrategist", val(toStrategist)])
        table.append(["toGovernance", val(toGovernance)])
        table.append(["toBadgerTree", val(toBadgerTree)])

        print(tabulate(table, headers=["account", "value"]))

    def printHarvestRewardsState(self, tx):

        events = tx.events
        event = events['HarvestBadgerState'][0]

        badgerHarvested = event['badgerHarvested']
        badgerConvertedToWbtc = event['badgerConvertedToWbtc']
        wtbcFromConversion = event['wtbcFromConversion']
        lpGained = event['lpGained']

        table = []
        console.print("[blue]== Harvest Badger State ==[/blue]")

        table.append(["badgerHarvested", val(badgerHarvested)])
        table.append(["badgerConvertedToWbtc", val(badgerConvertedToWbtc)])
        table.append(["wtbcFromConversion", val(wtbcFromConversion)])
        table.append(["lpGained", val(lpGained)])

        print(tabulate(table, headers=["account", "value"]))
        
    def confirm_harvest_events(self, before, after, tx):
        events = tx.events
        self.printHarvestState(tx)
        self.printHarvestRewardsState(tx)


        assert True