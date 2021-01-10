from brownie import DiggRewardsFaucet

from tests.sett.fixtures.DiggSettMiniDeployBase import DiggSettMiniDeployBase
from config.badger_config import sett_config, digg_config_test


class DiggRewardsMiniDeploy(DiggSettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.badger.params
        params.want = self.digg.token
        want = params.want

        self.badger.deploy_logic("DiggRewardsFaucet", DiggRewardsFaucet)

        self.rewards = self.badger.deploy_digg_rewards_faucet(
            self.key, self.digg.token
        )

        params.geyser = self.rewards

        return (params, want)

    def post_deploy_setup(self):
        """
        Distribute badger to Geyser and allow strategy to take
        """
        super().post_deploy_setup()

        self.badger.distribute_staking_rewards(
            self.key, digg_config_test.geyserParams.unlockSchedules.digg[0].amount
        )

        # Make strategy the recipient of the DIGG faucet
        self.rewards.initializeRecipient(self.strategy, {"from": self.deployer})
