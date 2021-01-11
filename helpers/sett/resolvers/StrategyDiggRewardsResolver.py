from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyDiggRewardsResolver(StrategyCoreResolver):
    # ===== Strategies must implement =====

    def confirm_harvest(self, before, after, tx):
        strategy = self.manager.strategy
        # rewards = interface.IDiggRewardsFaucet(strategy.geyser())
        super().confirm_harvest(before, after, tx)
        # table = []
        # table.append(["sett.keeper", self.sett.keeper()])
        # print(tabulate(table, headers=["account", "value"]))
        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert after.get("strategy.balanceOf") >= before_balance if before_balance else 0

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "diggFaucet": strategy.diggFaucet(),
        }
