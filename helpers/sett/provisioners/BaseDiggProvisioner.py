import random

from helpers.token_utils import distribute_from_whale


class BaseDiggProvisioner:
    def __init__(self, manager):
        self.manager = manager

    def _distributeTokens(self):
        # Distribute full randomized percentage in first iteration.
        # Subsequent iterations will see a randomized percentage of
        # remaining distribute to create a wide distribution spectrum
        # and to ensure that there is enough balance to distribute.
        remaining = 1
        # Distribute tokens from configured whales.
        for user in self.users:
            # Distibute a random percentage of remaining.
            percentage = random.random() * remaining
            for whale in self.whales:
                distribute_from_whale(
                    whale,
                    user,
                    percentage=percentage,
                )

            # Explicitly distribute digg.
            deployer = self.manager.deployer
            digg = self.manager.badger.digg_system.token
            balance = digg.balanceOf(deployer)
            digg.transfer(
                user,
                balance * percentage,
                {"from": deployer}
            )

            self._distributeWant()

    def _distributeWant(self):
        raise Exception("unimplemented")
