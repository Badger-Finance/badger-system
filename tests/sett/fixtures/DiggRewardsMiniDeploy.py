from scripts.systems.digg_minimal import deploy_digg_minimal
from helpers.constants import APPROVED_STAKER_ROLE
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config, digg_config_test
from helpers.registry import registry
from brownie import *

class DiggRewardsMiniDeploy(SettMiniDeployBase):
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
        self.badger.distribute_staking_rewards(
            self.key, digg_config_test.geyserParams.unlockSchedules.digg[0].amount
        )

        # Make strategy the recipient of the DIGG faucet
        self.rewards.initializeRecipient(self.strategy, {"from": self.deployer})

        # Track our digg system within badger system for convenience
        self.badger.add_existing_digg(self.digg)

    def pre_deploy_setup(self):
        """
        Deploy DIGG System
        Deploy StakingRewards for Strategy
        """
        devProxyAdminAddress = web3.toChecksumAddress("0x20dce41acca85e8222d6861aa6d23b6c941777bf")
        daoProxyAdminAddress = web3.toChecksumAddress("0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2")
        self.digg = deploy_digg_minimal(
            self.deployer, devProxyAdminAddress, daoProxyAdminAddress, owner=self.deployer
        )


