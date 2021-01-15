import random
from typing import Any

from helpers.sett.SnapshotManager import SnapshotManager
from config.badger_config import digg_decimals
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
        self.snap.rebase(rebaseValue * 10**digg_decimals, {"from": self.user})


class DiggActor:
    def __init__(self, manager: Any, user: Any):
        self.snap = manager.snap
        self.user = user

    def generateAction(self) -> BaseAction:
        '''
        Only produces rebase action.
        '''
        return RebaseAction(self.snap, self.user)
