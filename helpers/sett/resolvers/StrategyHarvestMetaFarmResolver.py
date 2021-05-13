from brownie import *

from helpers.constants import *
from helpers.multicall import Call, func, as_wei
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyHarvestMetaFarmResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after, tx):
        super().confirm_harvest(before, after, tx)
        # Increase or constant in strategy want balance
        assert after.balances("want", "strategy") >= before.balances("want", "strategy")
        # No idle farm in strategy
        assert after.balances("farm", "strategy") == 0

        # Reduce FARM in vaultFarm (harvest rewards)
        assert after.get("vaultFarm.earned.strategy") == 0

        # Reduce FARM in metaFarm (unstake all FARM)
        assert after.get("metaFarm.staked.strategy") == 0

        # BadgerTree should gain FARM
        # TODO(bodu): Make test more granular later since we're actually
        # taking out strategist fees on FARM before distributing remaining
        # to the rewards tree.
        assert after.balances("farm", "badgerTree") > before.balances(
            "farm", "badgerTree"
        )

    def confirm_tend(self, before, after, tx):
        # All FARM from underlying vaults should be harvested
        assert before.get("vaultFarm.earned.strategy") >= after.get(
            "vaultFarm.earned.strategy"
        )
        assert before.get("metaFarm.earned.strategy") >= after.get(
            "metaFarm.earned.strategy"
        )

        # Collected rewards from all vaults are staked in metaVault
        assert after.get("metaFarm.staked.strategy") >= before.get(
            "metaFarm.staked.strategy"
        )

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "harvestVault": strategy.harvestVault(),
            "vaultFarm": strategy.vaultFarm(),
            "metaFarm": strategy.metaFarm(),
            "badgerTree": strategy.badgerTree(),
        }

    def confirm_migrate(self, before, after):
        """
        - Send all FARM to the rewards
        - Leave no FARM in Strategy
        - Leave no FARM in MetaFarm
        - Leave no FARM in VaultFarm
        - Leave no fShares in VaultFarm
        """
        assert False

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)

        # Add FARM token balances.
        farm = interface.IERC20(self.manager.strategy.farm())

        calls = self.add_entity_balances_for_tokens(calls, "farm", farm, entities)
        return calls

    def add_strategy_snap(self, calls, entities=None):
        super().add_strategy_snap(calls)

        strategy = self.manager.strategy

        calls.append(
            Call(
                strategy.vaultFarm(),
                [func.rewardPool.earned, strategy.address],
                [["vaultFarm.earned.strategy", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.vaultFarm(),
                [func.rewardPool.balanceOf, strategy.address],
                [["vaultFarm.staked.strategy", as_wei]],
            )
        )

        calls.append(
            Call(
                strategy.metaFarm(),
                [func.rewardPool.earned, strategy.address],
                [["metaFarm.earned.strategy", as_wei]],
            )
        )
        calls.append(
            Call(
                strategy.metaFarm(),
                [func.rewardPool.balanceOf, strategy.address],
                [["metaFarm.staked.strategy", as_wei]],
            )
        )

        return calls
