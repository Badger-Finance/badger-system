from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class SushiClawUSDCProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            # collateral tokens (used to mint synthetic)
            registry.whales.bBadger,
            registry.whales.bSushiWbtcEth,
            # lp pair
            registry.whales.usdc,
        ]

    def _distributeWant(self, users) -> None:
        claw = self.manager.badger.claw
        # Generate lp tokens for users.
        for user in users:
            # Mint some synthetic tokens.
            claw.mint(user)
            sushiswap = SushiswapSystem()
            # Generate lp tokens.
            sushiswap.addMaxLiquidity(
                claw.emp.tokenCurrency(),
                registry.tokens.usdc,
                user,
            )
