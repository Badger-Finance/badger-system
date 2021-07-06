from brownie import chain
from rich.console import Console

from config.badger_config import digg_config
from .SnapshotManager import SnapshotManager

console = Console()

class DiggStabilizerSnapshotManager(SnapshotManager):
    def rebalance(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        tx = self.strategy.rebalance(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_rebalance(before, after, tx)
