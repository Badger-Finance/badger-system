import random
from brownie import Wei

from helpers.token_utils import distribute_from_whale, distribute_test_ether


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
                # Explicitly distribute digg to users from ls.
                digg = self.manager.badger.digg
                balance = digg.token.balanceOf(digg.daoDiggTimelock)
                digg.token.transfer(
                    user,
                    balance * percentage,
                    {"from": digg.daoDiggTimelock},
                )

    def _distributeWant(self, users) -> None:
        raise Exception("unimplemented")
