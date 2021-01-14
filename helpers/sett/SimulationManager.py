import time
import random
from brownie import accounts
from enum import Enum
from rich.console import Console

from scripts.systems.badger_system import BadgerSystem
from .SnapshotManager import SnapshotManager
from .provisioners import (
    DiggRewardsProvisioner,
    DiggLpMetaFarmProvisioner,
    SushiDiggWbtcLpOptimizerProvisioner,
)

console = Console()

# Provision num users for sim.
NUM_USERS = 10


class SimulationManagerState(Enum):
    IDLE = 0
    PROVISIONED = 1
    RANDOMIZED = 2
    RUNNING = 3


# SimulationManager is meant to be initialized per test and run once.
class SimulationManager:
    def __init__(
        self,
        badger: BadgerSystem,
        snap: SnapshotManager,
        settId: str,
    ):
        self.accounts = accounts[6:]  # use the 7th account onwards
        self.users = []  # users need to be provisioned before

        self.badger = badger
        self.snap = snap
        self.sett = badger.getSett(settId)
        self.strategy = badger.getStrategy(settId)
        self.want = badger.getStrategyWant(settId)
        self.settKeeper = accounts.at(self.sett.keeper(), force=True)
        self.strategyKeeper = accounts.at(self.strategy.keeper(), force=True)

        self.state = SimulationManagerState.IDLE

        # Track seed so we can hard code this value if we want to repro test failures.
        self.seed = int(time.time())
        random.seed(self.seed)
        self.provisioner = self.init_provisioner(self.strategy.getName())

    def provision(self):
        if self.state != SimulationManagerState.IDLE:
            raise Exception(f"invalid state: {self.state}")

        accountsUsed = set([])
        while len(self.users) < NUM_USERS:
            idx = int(random.random()*len(self.accounts))
            if idx in accountsUsed:
                continue

            self.users.append(self.accounts[idx])
            accountsUsed.add(idx)

        self._distributeTokens()
        self._distributeWant()

        self.state = SimulationManagerState.PROVISIONED

    def randomize(self):
        if self.state != SimulationManagerState.PROVISIONED:
            raise Exception(f"invalid state: {self.state}")
        self.state = SimulationManagerState.RANDOMIZED

    def run(self):
        if self.state != SimulationManagerState.RANDOMIZED:
            raise Exception(f"invalid state: {self.state}")
        self.state = SimulationManagerState.RUNNING

    def init_provisioner(self, name):
        if name == "StrategyDiggRewards":
            return DiggRewardsProvisioner(self)
        if name == "StrategyDiggLpMetaFarm":
            return DiggLpMetaFarmProvisioner(self)
        if name == "StrategySushiDiggWbtcLpOptimizer":
            return SushiDiggWbtcLpOptimizerProvisioner(self)
        raise Exception(f"invalid strategy name (no provisioner): {name}")

    def _distributeTokens(self):
        raise Exception("unimplemented")
