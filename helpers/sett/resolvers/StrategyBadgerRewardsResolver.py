from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyBadgerRewardsResolver(StrategyCoreResolver):
    # ===== Strategies must implement =====

    def confirm_harvest(self, before, after):
        super().confirm_harvest(before, after)
        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert after.get("strategy.balanceOf") >= before_balance if before_balance else 0

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get("sett.pricePerFullShare")

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "stakingRewards": strategy.geyser(),
        }
