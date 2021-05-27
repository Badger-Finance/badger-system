from helpers.constants import PAUSER_ROLE, UNPAUSER_ROLE
from helpers.time_utils import days
from brownie import DiggRewardsFaucet, chain

from tests.sett.fixtures.DiggSettMiniDeployBase import DiggSettMiniDeployBase
from config.badger_config import sett_config, digg_config_test


class DiggRewardsMiniDeploy(DiggSettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.badger.params
        params.want = self.digg.token
        want = params.want

        self.rewards = self.badger.deploy_digg_rewards_faucet(self.key, self.digg.token)

        params.geyser = self.rewards

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Distribute digg to Geyser and allow strategy to take
        """
        super().post_deploy_setup(deploy=deploy)

        if not deploy:
            return

        amount = digg_config_test.geyserParams.unlockSchedules.digg[0].amount
        digg = self.digg.token

        digg.transfer(self.rewards, amount, {"from": self.deployer})
        self.rewards.notifyRewardAmount(
            chain.time(),
            days(7),
            digg.fragmentsToShares(amount),
            {"from": self.deployer},
        )
        print(digg.balanceOf(self.rewards), digg.sharesOf(self.rewards))

        self.rewards.grantRole(PAUSER_ROLE, self.keeper, {"from": self.deployer})
        self.rewards.grantRole(UNPAUSER_ROLE, self.guardian, {"from": self.deployer})

        # Make strategy the recipient of the DIGG faucet
        self.rewards.initializeRecipient(self.strategy, {"from": self.deployer})
