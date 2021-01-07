from brownie import web3

from scripts.systems.digg_minimal import deploy_digg_minimal
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry


class SushiDiggWbtcLpOptimizerMiniDeploy(SettMiniDeployBase):
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

        return (params, want)

    def post_deploy_setup(self):
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
