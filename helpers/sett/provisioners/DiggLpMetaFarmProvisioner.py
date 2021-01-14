from scripts.systems.uniswap_system import UniswapSystem
from helpers.registry import registry
from .BaseDiggProvisioner import BaseDiggProvisioner


class DiggLpMetaFarmProvisioner(BaseDiggProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
        ]

    def _distributeWant(self):
        uniswap = UniswapSystem()
        # Generate lp tokens.
        uniswap.addMaxLiquidity(
            self.digg.token,
            registry.tokens.wbtc,
            self.manager.deployer,
        )
