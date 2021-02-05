import datetime
import json
import os
from scripts.actions.helpers.GeyserDistributor import GeyserDistributor
from scripts.actions.helpers.StakingRewardsDistributor import StakingRewardsDistributor
import time
import warnings

import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import initial_fragments_to_current_fragments, to_digg_shares, val
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()

def asset_to_address(asset):
    if asset == "badger":
        return "0x3472A5A71965499acd81997a54BBA8D852C6E53d"
    if asset == "digg":
        return "0x798D1bE841a82a273720CE31c822C61a67a601C3"


class RewardsDist:
    """
    Store the rewards distributions for a given asset
    """

    def __init__(self, key, amounts):
        self.key = key
        self.toGeyser = {}
        self.toStakingRewards = {}
        self.hasGeyserDist = True
        self.hasStakingRewardsDist = False

        # If compounding, split rewards between geyser & staking rewards
        for asset, amount in amounts.items():
            print(self.key, amount)
            if self.compounding_only(self.key, asset):
                print("Compounding Only", self.key, asset)
                # All to compounding
                self.toGeyser[asset] = 0
                self.toStakingRewards[asset] = amount
                self.hasGeyserDist = False
                self.hasStakingRewardsDist = True
            elif self.has_compounding(self.key, asset):
                print("Half Compounding", self.key, asset)
                # Split evenly between geyser & compounding
                self.toGeyser[asset] = amount // 2
                self.toStakingRewards[asset] = amount // 2
                self.hasStakingRewardsDist = True
            else:
                print("All to Geyser", self.key, asset)
                # All to geyser
                self.toGeyser[asset] = amount
                self.toStakingRewards[asset] = 0

    def getGeyserDistributions(self):
        return self.toGeyser

    def getStakingRewardsDistributions(self):
        return self.toStakingRewards

    def getToGeyser(self, asset):
        return self.toGeyser[asset]

    def getToStakingRewards(self, asset):
        return self.toStakingRewards[asset]

    def getToStakingRewardsDaily(self, asset):
        return self.toStakingRewards[asset] // 7

    def hasStakingRewardsDistribution(self):
        return self.hasStakingRewardsDist

    def hasGeyserDistribution(self):
        return self.hasGeyserDist

    def compounding_only(self, key, asset):
        if key == "native.digg" and asset == "digg":
            return True
        else:
            return False

    def has_compounding(self, key, asset):

        # Badger + badger LP have half auto compounding badger
        if (
            key == "native.badger"
            or key == "native.uniBadgerWbtc"
            or key == "native.sushiBadgerWbtc"
        ) and asset == "badger":
            return True
        # digg LP have half auto compounding DIGG
        elif (
            key == "native.uniDiggWbtc" or key == "native.sushiDiggWbtc"
        ) and asset == "digg":
            return True
        else:
            return False


class RewardsSchedule:
    def __init__(self, badger: BadgerSystem):
        self.badger = badger
        self.amounts = {}
        self.total = 0
        self.distributions = {}

    def getDistributions(self, key):
        return self.distributions[key]

    def setStart(self, timestamp):
        self.start = timestamp

    def setDuration(self, timestamp):
        self.duration = timestamp
        self.end = self.start + timestamp

    def setAmounts(self, amounts):
        for key, values in amounts.items():
            print(key,)
            self.distributions[key] = RewardsDist(key, values)

    def tokensPerDay(self, amount):
        return amount * days(1) / self.duration

    def getExpectedTotal(self, key):
        return self.expectedTotals[key]

    def setExpectedTotals(self, totals):
        self.expectedTotals = totals

    def testTransactions(self):
        rewardsEscrow = self.badger.rewardsEscrow
        multi = GnosisSafe(self.badger.devMultisig)

        # Setup
        accounts[7].transfer(multi.get_first_owner(), Wei("2 ether"))
        print(
            "Supplied ETH", accounts.at(multi.get_first_owner(), force=True).balance(),
        )

        badger = self.badger
        tree = self.badger.badgerTree

        before = badger.token.balanceOf(tree)
        top_up = Wei("149606.49 ether")
        top_up_digg = initial_fragments_to_current_fragments(89.94)

        # Top up Tree
        # TODO: Make the amount based on what we'll require for the next week
        id = multi.addTx(
            MultisigTxMetadata(description="Top up badger tree with Badger"),
            {
                "to": rewardsEscrow.address,
                "data": rewardsEscrow.transfer.encode_input(badger.token, tree, top_up),
            },
        )

        tx = multi.executeTx(id)

        after = badger.token.balanceOf(tree)
        assert after == before + top_up

        before = badger.digg.token.balanceOf(tree)

        multi.execute(
            MultisigTxMetadata(description="Top up badger tree with DIGG"),
            {
                "to": rewardsEscrow.address,
                "data": rewardsEscrow.transfer.encode_input(
                    badger.digg.token, tree, top_up_digg
                ),
            },
        )

        after = badger.digg.token.balanceOf(tree)
        assert after == before + top_up_digg

        for key, distribution in self.distributions.items():
            if distribution.hasGeyserDistribution() == True:
                print("has geyser distribution", key)
                GeyserDistributor(
                    badger,
                    multi,
                    key,
                    distributions=distribution.getGeyserDistributions(),
                    start=self.start,
                    duration=self.duration,
                    end=self.end,
                )

            # == Distribute to StakingRewards, if relevant ==
            # if distribution.hasStakingRewardsDistribution() == True:
            #     StakingRewardsDistributor(
            #         badger,
            #         multi,
            #         key,
            #         distributions=distribution.getStakingRewardsDistributions(),
            #         start=self.start,
            #         duration=self.duration,
            #         end=self.end,
            #         )
            

    def printState(self, title):
        console.print(
            "\n[yellow]=== 🦡 Rewards Schedule: {} 🦡 ===[/yellow]".format(title)
        )
        table = []

        rewardsEscrow = self.badger.rewardsEscrow
        for key, dist in self.distributions.items():
            if key == "native.digg":
                continue
            print(key, dist)
            geyser = self.badger.getGeyser(key)
            print(geyser)
            assert rewardsEscrow.isApproved(geyser)
            for asset, value in dist.toGeyser.items():
                
                """
                function signalTokenLock(
                    address geyser,
                    address token,
                    uint256 amount,
                    uint256 durationSec,
                    uint256 startTime
                )
                """

                encoded = rewardsEscrow.signalTokenLock.encode_input(
                    geyser, asset_to_address(asset), value, self.duration, self.start
                )

                table.append(
                    [
                        key,
                        geyser,
                        asset,
                        value,
                        val(value),
                        to_utc_date(self.start),
                        to_utc_date(self.end),
                        to_days(self.duration),
                        geyser.address,
                        encoded
                    ]
                )

        print(
            tabulate(
                table,
                headers=[
                    "key",
                    "geyser",
                    "token",
                    "total amount",
                    "scaled amount",
                    "start time",
                    "end time",
                    "duration",
                    "rate per day",
                    "destination",
                    "encoded call",
                ],
                tablefmt="rst",
            )
        )

        print("total distributed: ", val(self.total))

