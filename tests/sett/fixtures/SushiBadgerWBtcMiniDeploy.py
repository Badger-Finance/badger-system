from helpers.constants import APPROVED_STAKER_ROLE
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.registry import registry


class SushiBadgerWBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.sushi.sushiBadgerWBtc.params

        sushiswap = SushiswapSystem()
        want = sushiswap.getPair(self.badger.token, registry.tokens.wbtc)

        params.want = want
        params.badgerTree = self.badger.badgerTree
        params.badger = self.badger.token

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Distribute badger to Geyser and allow strategy to take
        Unpause strategy (paused on initialization)
        """
        if not deploy:
            return
        self.badger.distribute_staking_rewards(
            self.key, badger_config.geyserParams.unlockSchedules.badger[0].amount
        )

        self.rewards.initializeApprovedStaker(self.strategy, {"from": self.deployer})

        # Generate initial LP tokens and grant to deployer
        # sushiswap = SushiswapSystem()
        # pid = sushiswap.add_chef_rewards(self.want)
        # print(pid)
        # assert pid == self.strategy.pid()

    def post_vault_deploy_setup(self, deploy=True):
        """
        Deploy StakingRewardsSignalOnly for Strategy
        """
        if not deploy:
            return

        self.rewards = self.badger.deploy_sett_staking_rewards_signal_only(
            self.key, self.deployer, self.badger.token
        )

        self.params.geyser = self.rewards
