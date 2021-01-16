import random

from helpers.token_utils import distribute_from_whale


class BaseProvisioner:
    def __init__(self, manager):
        self.manager = manager

    def _distributeTokens(self, users) -> None:
        # Distribute full randomized percentage in first iteration.
        # Subsequent iterations will see a randomized percentage of
        # remaining distribute to create a wide distribution spectrum
        # and to ensure that there is enough balance to distribute.
        remaining = 1
        # Distribute tokens from configured whales.
        for user in users:
            # Distibute a random percentage of remaining.
            percentage = random.random() * remaining
            for whale in self.whales:
                distribute_from_whale(
                    whale,
                    user,
                    percentage=percentage,
                )

            if self.manager.badger.digg is not None:
                # Explicitly distribute digg to users from deployer.
                deployer = self.manager.badger.deployer
                digg = self.manager.badger.digg.token
                balance = digg.balanceOf(deployer)
                digg.transfer(
                    user,
                    balance * percentage,
                    {"from": deployer},
                )

    def _distributeWant(self, users) -> None:
        raise Exception("unimplemented")
