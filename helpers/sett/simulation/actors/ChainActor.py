import random
from brownie import chain

from helpers.time_utils import days
from .BaseAction import BaseAction


class MineAction(BaseAction):
    def run(self):
        chain.mine()


class SleepAction(BaseAction):
    def run(self):
        chain.sleep(days(random.random() * random.randrange(10)))


class ChainActor:
    def __init__(self):
        self.randomActions = [
            MineAction(),
            SleepAction(),
        ]

    def generateAction(self) -> BaseAction:
        """
        Produces random actions. (Mine or Sleep)
        """
        idx = int(random.random() * len(self.randomActions))
        return self.randomActions[idx]
