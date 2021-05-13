from brownie import chain, DiggRewardsFaucet

from tests.sett.fixtures.DiggSettMiniDeployBase import DiggSettMiniDeployBase
from config.badger_config import sett_config, digg_config_test
from scripts.systems.uniswap_system import UniswapSystem
from helpers.registry import registry
from helpers.constants import PAUSER_ROLE, UNPAUSER_ROLE
from helpers.time_utils import days
from rich.console import Console

console = Console()


class UniDiggWbtcLpMiniDeploy(DiggSettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.uni.uniDiggWbtc.params

        uniswap = UniswapSystem()
        # TODO: Pull digg token addr from registry once its deployed.
        if uniswap.hasPair(self.digg.token, registry.tokens.wbtc):
            params.want = uniswap.getPair(self.digg.token, registry.tokens.wbtc)
        else:
            params.want = uniswap.createPair(
                self.digg.token, registry.tokens.wbtc, self.deployer,
            )
        want = params.want
        params.token = self.digg.token

        self.badger.deploy_logic("DiggRewardsFaucet", DiggRewardsFaucet, test=True)
        self.rewards = self.badger.deploy_digg_rewards_faucet(self.key, self.digg.token)

        params.geyser = self.rewards

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Distribute digg to geyser and allow strategy to take
        """
        super().post_deploy_setup(deploy=deploy)

        # Track our digg system within badger system for convenience.
        self.badger.add_existing_digg(self.digg)

        if not deploy:
            return

        digg = self.digg.token
        # Transfer initial emissions to DiggFaucet
        amount = digg_config_test.geyserParams.unlockSchedules.digg[0].amount
        digg.transfer(self.rewards, amount, {"from": self.deployer})
        self.rewards.notifyRewardAmount(
            chain.time(),
            days(7),
            digg.fragmentsToShares(amount),
            {"from": self.deployer},
        )

        self.rewards.grantRole(PAUSER_ROLE, self.keeper, {"from": self.deployer})
        self.rewards.grantRole(UNPAUSER_ROLE, self.guardian, {"from": self.deployer})

        # Make strategy the recipient of the DIGG faucet
        self.rewards.initializeRecipient(self.strategy, {"from": self.deployer})

        if self.strategy.paused():
            self.strategy.unpause({"from": self.governance})

    def post_vault_deploy_setup(self, deploy=True):
        """
        Generate LP tokens and grant to deployer
        """
        if not deploy:
            return
        uniswap = UniswapSystem()
        # Generate lp tokens.
        uniswap.addMaxLiquidity(
            self.digg.token, registry.tokens.wbtc, self.deployer,
        )
