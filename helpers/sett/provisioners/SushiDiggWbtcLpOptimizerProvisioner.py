from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry
from .BaseDiggProvisioner import BaseDiggProvisioner


class SushiDiggWbtcLpOptimizerProvisioner(BaseDiggProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
        ]

    def _distributeWant(self):
        sushiswap = SushiswapSystem()
        # Generate lp tokens.
        sushiswap.addMaxLiquidity(
            self.digg.token,
            registry.tokens.wbtc,
            self.manager.deployer,
        )
