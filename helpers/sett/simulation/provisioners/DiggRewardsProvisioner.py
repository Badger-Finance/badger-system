from .BaseProvisioner import BaseProvisioner


class DiggRewardsProvisioner(BaseProvisioner):
    def _distributeWant(self, users) -> None:
        # NB: Digg is distributed as part of token
        # distribution in the base provisioner so there's
        # nothing to do here.
        pass
