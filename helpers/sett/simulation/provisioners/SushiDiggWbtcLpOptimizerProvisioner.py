from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class SushiDiggWbtcLpOptimizerProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
        ]

    def _distributeWant(self, users) -> None:
        digg = self.manager.badger.digg
        # Generate lp tokens for users.
        for user in users:
            sushiswap = SushiswapSystem()
            # Generate lp tokens.
            sushiswap.addMaxLiquidity(
                digg.token,
                registry.tokens.wbtc,
                user,
            )
