from tests.sett.fixtures.DiggSettMiniDeployBase import DiggSettMiniDeployBase
from config.badger_config import sett_config, digg_config_test
from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry


class SushiDiggWbtcLpOptimizerMiniDeploy(DiggSettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.sushi.sushiDiggWBtc.params

        sushiswap = SushiswapSystem()
        # TODO: Pull digg token addr from registry once its deployed.
        if sushiswap.hasPair(self.digg.token, registry.tokens.wbtc):
            params.want = sushiswap.getPair(self.digg.token, registry.tokens.wbtc)
        else:
            params.want = sushiswap.createPair(
                self.digg.token,
                registry.tokens.wbtc,
                self.deployer,
            )
        want = params.want
        params.token = self.digg.token
        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_deploy_setup(self):
        """
        Distribute digg to geyser and allow strategy to take
        """
        # Track our digg system within badger system for convenience.
        self.badger.add_existing_digg(self.digg)

        self.badger.distribute_staking_rewards(
            self.key,
            digg_config_test.geyserParams.unlockSchedules.digg[0].amount,
        )

        self.rewards.initializeApprovedStaker(self.strategy, {"from": self.deployer})

        if self.strategy.paused():
            self.strategy.unpause({"from": self.governance})

    def post_vault_deploy_setup(self):
        """
        Deploy StakingRewardsSignalOnly for Digg Strategy
        Generate LP tokens and grant to deployer
        """

        # rewards in digg, stake in sushi (ONLY SIGNAL)
        self.rewards = self.badger.deploy_sett_staking_rewards_signal_only(
            self.key, self.deployer, self.digg.token
        )

        self.params.geyser = self.rewards

        # Setup sushi reward allocations.
        sushiswap = SushiswapSystem()
        pid = sushiswap.add_chef_rewards(self.want)
        # Generate lp tokens.
        sushiswap.addMaxLiquidity(
            self.digg.token,
            registry.tokens.wbtc,
            self.deployer,
        )

        # Pass in LP token pool id to underlying strategy.
        self.params.pid = pid
