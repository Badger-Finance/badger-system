from rich.console import Console
from assistant.rewards.aws_utils import upload_analytics
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from helpers.constants import BADGER, DIGG
import numpy as np
import json

console = Console()


class RewardsLog:
    def __init__(self):
        self._totalTokenDist = {}
        self._merkleRoot = ""
        self._contentHash = ""
        self._startBlock = 0
        self._endBlock = 0

    def set_merkle_root(self, root):
        self._merkleRoot = root

    def set_content_hash(self, content_hash):
        self._contentHash = content_hash

    def set_start_block(self, startBlock):
        self._startBlock = startBlock

    def set_end_block(self, endBlock):
        self._endBlock = endBlock

    def add_total_token_dist(self, name, token, amount):
        if name not in self._totalTokenDist:
            self._totalTokenDist[name] = {}
        self._totalTokenDist[name][token] = amount

    def save(self, cycle):

        data = {
            "cycle": cycle,
            "merkleRoot": self._merkleRoot,
            "contentHash": self._contentHash,
            "startBlock": self._startBlock,
            "endBlock": self._endBlock,
            "totalTokenDist": self._totalTokenDist,
        }

        upload_analytics(cycle, data)


rewardsLog = RewardsLog()
