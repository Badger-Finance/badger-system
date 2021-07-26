from scripts.systems.pancakeswap_system import PancakeswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class PancakeBnbBtcbProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            # lp pair tokens
            registry.whales.bnb,
            registry.whales.btcb,
        ]

    def _distributeWant(self, users) -> None:
        # Generate lp tokens for users.
        for user in users:
            pancakeswap = PancakeswapSystem()
            # Generate lp tokens.
            pancakeswap.addMaxLiquidity(
                registry.tokens.bnb,
                registry.tokens.btcb,
                user,
            )
