from scripts.systems.pancakeswap_system import PancakeswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner
from brownie import chain, interface, accounts
from helpers.constants import MaxUint256


class PancakeBBadgerBtcbProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            # lp pair tokens
            registry.whales.pancakebBadgerbtcb
        ]

    def _distributeWant(self, users) -> None:
        # Generate lp tokens for users.
        for user in users:
            pancakeswap = PancakeswapSystem(version=2)
            # Generate lp tokens.
            router = interface.IPancakeRouter02(
                "0x10ED43C718714eb63d5aA57B78B54704E256024E"
            )
