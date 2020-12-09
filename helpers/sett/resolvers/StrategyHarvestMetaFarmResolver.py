from brownie import *
from helpers.constants import *
from multicall import Call, Multicall
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver

"""
if name == "StrategyHarvestMetaFarm":
        farm = interface.IERC20(strategy.farm())
        harvestVault = interface.IHarvestVault(strategy.harvestVault())
        vaultFarm = interface.IRewardPool(strategy.harvestVault())
        metaFarm = interface.IRewardPool(strategy.harvestVault())
        badgerTree = interface.IERC20(strategy.badgerTree())

        result.contracts.harvestVault = harvestVault
        result.contracts.farm = farm
        result.contracts.vaultFarm = vaultFarm
        result.contracts.metaFarm = metaFarm
        result.contracts.badgerTree = badgerTree

        result.strategy.farmBalance = farm.balanceOf(strategy)

        result.strategy.harvestVault.stakedShares = harvestVault.balanceOf(strategy)
        result.strategy.harvestVault.stakedSharesInFarm = vaultFarm.balanceOf(strategy)
        result.strategy.harvestVault.pricePerFullShare = (
            harvestVault.getPricePerFullShare()
        )
        result.strategy.metaFarm.stakedFarm = metaFarm.balanceOf(strategy)
        result.badgerTree.farm = farm.balanceOf(badgerTree)
    return result
"""


class StrategyHarvestMetaFarmResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after):
        """
        Harvest Should;
        - Increase the balanceOf() underlying asset in the Strategy
        - Reduce the amount of idle FARM to zero
        - Reduce FARM in vaultFarm to zero
        - Reduce FARM in metaFarm to zero
        - Increase the ppfs on sett1
        """

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

        # Increase or constant in PPFS

    def confirm_tend(self):
        assert True

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
