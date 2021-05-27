from helpers.multicall import func, as_wei, Call
from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyBadgerRewardsResolver(StrategyCoreResolver):
    # ===== Strategies must implement =====

    def confirm_harvest(self, before, after, tx):
        super().confirm_harvest(before, after, tx)
        # Strategy want should increase
        before_balance = before.get("strategy.balanceOf")
        assert (
            after.get("strategy.balanceOf") >= before_balance if before_balance else 0
        )

        # PPFS should not decrease
        assert after.get("sett.pricePerFullShare") >= before.get(
            "sett.pricePerFullShare"
        )

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "stakingRewards": strategy.geyser(),
        }

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
