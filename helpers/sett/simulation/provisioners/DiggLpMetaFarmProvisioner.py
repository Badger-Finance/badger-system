from scripts.systems.uniswap_system import UniswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class DiggLpMetaFarmProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
        ]

    def _distributeWant(self, users) -> None:
        # Generate lp tokens for users.
        for user in users:
            uniswap = UniswapSystem()
            uniswap.addMaxLiquidity(
                self.digg.token,
                registry.tokens.wbtc,
                user,
            )
