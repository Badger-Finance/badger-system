from typing import Any

from helpers.sett.SnapshotManager import SnapshotManager
from .BaseAction import BaseAction


class SettEarnAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        keeper: Any,
    ):
        self.snap = snap
        self.keeper = keeper

    def run(self):
        self.snap.settEarn({"from": self.keeper})


class SettKeeperActor:
    def __init__(self, manager: Any, keeper: Any):
        self.snap = manager.snap
        self.keeper = keeper

    def generateAction(self) -> BaseAction:
        """
        Only produces sett earn action.
        """
        return SettEarnAction(self.snap, self.keeper)
