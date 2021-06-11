from scripts.systems.sushiswap_system import SushiswapSystem
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from helpers.registry import registry


class SushiWbtcIbBtcLpOptimizerMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.sushi.sushiWbtcIbBtc.params

        sushiswap = SushiswapSystem()
        if sushiswap.hasPair(registry.tokens.ibbtc, registry.tokens.wbtc):
            params.want = sushiswap.getPair(registry.tokens.ibbtc, registry.tokens.wbtc)
        else:
            params.want = sushiswap.createPair(
                registry.tokens.ibbtc,
                registry.tokens.wbtc,
                self.deployer,
            )

        want = params.want
        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        """
        Setup sushi rewards.
        """
        if not deploy:
            return

        # Setup sushi reward allocations.
        sushiswap = SushiswapSystem()
        pid = sushiswap.add_chef_rewards(self.want)

        # Pass in LP token pool id to underlying strategy.
        self.params.pid = pid
