from rich.console import Console

from .SnapshotManager import SnapshotManager

console = Console()


class DiggSnapshotManager(SnapshotManager):
    # Rebase digg assets at provided value.
    def rebase(self, value, overrides, confirm=True):
        console.print(f"rebasing at value: {value}")
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        _value = self.badger.digg_system.dynamicOracle.setValueAndPush(value)
        assert _value == value
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_rebase(before, after, value)
