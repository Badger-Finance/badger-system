from helpers.constants import APPROVED_STAKER_ROLE
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class BadgerRewardsMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.badger.params
        params.want = self.badger.token
        params.geyser = self.rewards

        want = self.badger.token

        return (params, want)

    def post_deploy_setup(self):
        """
        Distribute badger to Geyser and allow strategy to take
        """
        self.badger.distribute_staking_rewards(
            self.key, badger_config.geyserParams.unlockSchedules.badger[0].amount
        )

        # Approve Setts on specific
        self.rewards.grantRole(
            APPROVED_STAKER_ROLE, self.strategy, {"from": self.deployer}
        )

    def pre_deploy_setup(self):
        """
        Deploy StakingRewards for Strategy
        """
        self.rewards = self.badger.deploy_sett_staking_rewards(
            self.key, self.badger.token, self.badger.token
        )
