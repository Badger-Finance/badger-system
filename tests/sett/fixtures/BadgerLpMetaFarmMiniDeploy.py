from scripts.systems.uniswap_system import UniswapSystem
from config.badger_config import badger_config, sett_config
from helpers.constants import APPROVED_STAKER_ROLE
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from helpers.registry import registry


class BadgerLpMetaFarmMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.uniBadgerWbtc.params

        uniswap = UniswapSystem()
        want = uniswap.getPair(self.badger.token, registry.tokens.wbtc)

        params.want = want

        params.geyser = self.rewards

        return (params, want)

    def post_deploy_setup(self, deploy=True):
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

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy StakingRewards for Strategy
        """
        uniswap = UniswapSystem()
        want = uniswap.getPair(self.badger.token, registry.tokens.wbtc)

        self.rewards = self.badger.deploy_sett_staking_rewards(
            self.key, want, self.badger.token
        )
