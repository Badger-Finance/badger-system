import random
from typing import Any

from helpers.sett.SnapshotManager import SnapshotManager
from .BaseAction import BaseAction


class SettHarvestAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        keeper: Any,
    ):
        self.snap = snap
        self.keeper = keeper

    def run(self):
        self.snap.settHarvest({"from": self.keeper})


class SettTendAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        keeper: Any,
    ):
        self.snap = snap
        self.keeper = keeper

    def run(self):
        self.snap.settTend({"from": self.keeper})


class StrategyKeeperActor:
    def __init__(self, manager: Any, keeper: Any):
        self.snap = manager.snap
        self.keeper = keeper

        self.randomActions = [
            SettHarvestAction(self.snap, self.keeper),
        ]
        if manager.strategy.isTendable():
            self.randomActions.append(
                SettTendAction(
                    self.snap,
                    self.keeper,
                )
            )

    def generateAction(self) -> BaseAction:
        """
        Produces random actions. (Tend or Harvest)
        """
        idx = int(random.random() * len(self.randomActions))
        return self.randomActions[idx]
