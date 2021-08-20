from helpers.constants import APPROVED_STAKER_ROLE
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.token_utils import distribute_from_whales


class BadgerRewardsMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.badger.params
        params.want = self.badger.token
        params.geyser = self.rewards

        want = self.badger.token

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Distribute badger to Geyser and allow strategy to take
        """
        distribute_from_whales(self.deployer, 1, "badger")
        self.badger.distribute_staking_rewards(
            self.key, badger_config.geyserParams.unlockSchedules.badger[0].amount
        )

        # Approve Setts on specific
        self.rewards.grantRole(
            APPROVED_STAKER_ROLE, self.strategy, {"from": self.deployer}
        )

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy StakingRewards for Strategy
        """
        self.badger.deploy_staking_rewards_logic()
        self.rewards = self.badger.deploy_sett_staking_rewards(
            self.key, self.badger.token, self.badger.token
        )
