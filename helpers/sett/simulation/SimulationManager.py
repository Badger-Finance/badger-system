import time
import random
from brownie import accounts
from enum import Enum
from rich.console import Console

from scripts.systems.badger_system import BadgerSystem
from ..SnapshotManager import SnapshotManager
from .provisioners import (
    BaseProvisioner,
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
    RUN = 3


# SimulationManager is meant to be initialized per test and run once.
class SimulationManager:
    def __init__(
        self,
        badger: BadgerSystem,
        snap: SnapshotManager,
        settId: str,
    ):
        self.accounts = accounts[6:]  # Use the 7th account onwards.
        # User accounts (need to be provisioned before running sim).
        self.users = []
        # Actors are generators that yield valid actions based on
        # the actor type. For example, user actors need to have deposited
        # first before they can withdraw (withdraw before deposit is an
        # invalid action).
        self.actors = []

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
        self.provisioner = self._initProvisioner(self.strategy.getName())

    def provision(self) -> None:
        if self.state != SimulationManagerState.IDLE:
            raise Exception(f"invalid state: {self.state}")

        accountsUsed = set([])
        while len(self.users) < NUM_USERS:
            idx = int(random.random()*len(self.accounts))
            if idx in accountsUsed:
                continue

            self.users.append(self.accounts[idx])
            accountsUsed.add(idx)

        self._distributeTokens(self.users)
        self._distributeWant(self.users)

        self.state = SimulationManagerState.PROVISIONED

    def randomize(self) -> None:
        if self.state != SimulationManagerState.PROVISIONED:
            raise Exception(f"invalid state: {self.state}")
        self.state = SimulationManagerState.RANDOMIZED

    def run(self) -> None:
        if self.state != SimulationManagerState.RANDOMIZED:
            raise Exception(f"invalid state: {self.state}")
        self.state = SimulationManagerState.RUN

    def _initProvisioner(self, name) -> BaseProvisioner:
        if name == "StrategyDiggRewards":
            return DiggRewardsProvisioner(self)
        if name == "StrategyDiggLpMetaFarm":
            return DiggLpMetaFarmProvisioner(self)
        if name == "StrategySushiDiggWbtcLpOptimizer":
            return SushiDiggWbtcLpOptimizerProvisioner(self)
        raise Exception(f"invalid strategy name (no provisioner): {name}")

    def _provisionAccounts(self) -> None:
        pass
