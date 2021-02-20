from .BaseProvisioner import BaseProvisioner


class DiggRewardsProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # No other tokens to be distributed from whales.
        self.whales = []

    def _distributeWant(self, users) -> None:
        # NB: Digg is distributed as part of token
        # distribution in the base provisioner so there's
        # nothing to do here.
        pass
