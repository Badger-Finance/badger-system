from brownie import *
from helpers.constants import *
from multicall import Call, Multicall
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyHarvestMetaFarmResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after):
        super().confirm_harvest(before, after)
        # Increase or constant in strategy want balance
        assert after.balances("want", "strategy") >= before.balances("want", "strategy")
        # No idle farm in strategy
        assert after.balances("farm", "strategy") == 0

        # Reduce FARM in vaultFarm
        assert after.get("vaultFarm.earned.strategy") == 0

        # Reduce FARM in metaFarm
        assert after.get("metaFarm.staked.strategy") == 0

        # BadgerTree should gain FARM
        assert after.balances("farm", "badgerTree") > before.balances(
            "farm", "badgerTree"
        )

    def confirm_tend(self, before, after):
        # Amount of underlying in vault should not decrease
        assert after.balances("harvestVault", "strategy") >= after.balances(
            "harvestVault", "strategy"
        )

        # Amount of underlying staked in farm should not decrease
        assert after.balances("vaultFarm", "strategy") >= after.balances(
            "vaultFarm", "strategy"
        )

        # All FARM from underlying vault should be harvested
        assert after.balances("vaultFarm.strategy.earned") == 0

        # Amount of FARM in meta farm should increase
        assert after.balances("metaFarm", "strategy") >= after.balances(
            "metaFarm", "strategy"
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
