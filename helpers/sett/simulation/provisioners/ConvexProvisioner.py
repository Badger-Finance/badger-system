from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class ConvexProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.renCrv,
            registry.whales.sbtcCrv,
            registry.whales.tbtcCrv,
            registry.whales.hbtcCrv,
            registry.whales.pbtcCrv,
            registry.whales.obtcCrv,
            registry.whales.bbtcCrv,
            registry.whales.triCrypto,
            registry.whales.triCryptoDos,
        ]

    def _distributeWant(self, users) -> None:
        # no-op
        pass
