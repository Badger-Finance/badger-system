import random
from typing import Any

from helpers.sett.SnapshotManager import SnapshotManager
from .BaseAction import BaseAction


class RebaseAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        user: Any,
    ):
        self.snap = snap
        self.user = user

    def run(self):
        rebaseValue = random.random() * random.randint(1, 10)
        # Rebase values are expected to have 18 decimals of precision.
        self.snap.rebase(rebaseValue * 10 ** 18, {"from": self.user})


class DiggActor:
    def __init__(self, manager: Any, user: Any):
        self.snap = manager.snap
        self.user = user

    def generateAction(self) -> BaseAction:
        """
        Only produces rebase action.
        """
        return RebaseAction(self.snap, self.user)
