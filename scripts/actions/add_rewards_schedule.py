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
from helpers.utils import to_digg, to_digg_shares, val
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
            key == "native.uniDiggWbtc"
            or key == "native.sushiDiggWbtc"
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
        top_up = Wei("200000 ether")
        top_up_digg = to_digg(192.38 / 2)

        # Top up Tree
        # TODO: Make the amount based on what we'll require for the next week
        id = multi.addTx(
            MultisigTxMetadata(
                description="Top up badger tree with Badger"
            ),
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
            MultisigTxMetadata(
                description="Top up badger tree with DIGG"
            ),
            {
                "to": rewardsEscrow.address,
                "data": rewardsEscrow.transfer.encode_input(badger.digg.token, tree, top_up_digg),
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
        for key, amount in self.amounts.items():
            geyser = self.badger.getGeyser(key)
            assert rewardsEscrow.isApproved(geyser)

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
                geyser, self.badger.token, amount, self.duration, self.start
            )

            table.append(
                [
                    key,
                    geyser,
                    self.badger.token,
                    val(amount),
                    to_utc_date(self.start),
                    to_utc_date(self.end),
                    to_days(self.duration),
                    val(self.tokensPerDay(amount)),
                    # self.badger.rewardsEscrow,
                    # encoded,
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
                    "start time",
                    "end time",
                    "duration",
                    "rate per day",
                    # "destination",
                    # "encoded call",
                ],
                tablefmt="rst",
            )
        )

        print("total distributed: ", val(self.total))


def main():
    badger = connect_badger("deploy-final.json")
    admin = badger.devProxyAdmin
    multisig = badger.devMultisig
    contracts = badger.contracts_upgradeable
    deployer = badger.deployer

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert multisig == expectedMultisig

    """
    Total $BADGER 603,750

    Setts
    renbtcCRV — 83,437.5 $BADGER
    sbtcCRV — 83,437.5 $BADGER
    tbtcCRV — 83,437.5 $BADGER
    Badger — 70,000 $BADGER
    (NEW) wBTC/ETH Sushiswap LP — 40,000 $BADGER
    Badger <>wBTC Uniswap LP — 110,000 $BADGER
    (NEW) Badger <>wBTC Sushiswap LP— 50,000 $BADGER

    wbtc/eth = 34,285 $BADGER (which should be distributed evenly over 3 days ie today 1pm to tomorrow, tomorrow to wednesday, wed- thursday then new emissions)
    Badger <>wBTC Sushiswap LP— 30,000 $BADGER (10k/day)

    Super Sett
    Harvest renbtc CRV —83,437.5 $BADGER
    """

    rest = RewardsSchedule(badger)

    rest.setStart(to_timestamp(datetime.datetime(2021, 1, 28, 12, 00)))
    rest.setDuration(days(7))

    rest.setAmounts(
        {
            "native.uniBadgerWbtc": {
                "badger": Wei("25897 ether"),
                "digg": to_digg_shares(17.86),
            },
            "native.sushiBadgerWbtc": {
                "badger": Wei("25897 ether"),
                "digg": to_digg_shares(17.86),
            },
            "native.badger": {"badger": Wei("12949 ether"), "digg": to_digg_shares(8.93)},
            "native.sushiWbtcEth": {
                "badger": Wei("20253 ether"),
                "digg": to_digg_shares(13.97),
            },
            "native.renCrv": {"badger": Wei("20253 ether"), "digg": to_digg_shares(13.97)},
            "native.sbtcCrv": {"badger": Wei("20253 ether"), "digg": to_digg_shares(13.97)},
            "native.tbtcCrv": {"badger": Wei("20253 ether"), "digg": to_digg_shares(13.97)},
            "harvest.renCrv": {"badger": Wei("20253 ether"), "digg": to_digg_shares(13.97)},
            "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(31.16)},
            "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(31.16)},
            "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(15.58)},
        }
    )

    rest.setExpectedTotals({"badger": Wei("166008 ether"), "digg": to_digg_shares(192.38)})

    rest.testTransactions()

    rest.printState("Week ?? - who knows anymore")

    # print("overall total ", total)
    # print("expected total ", expected)

    # assert total == expected

    # console.print(
    #     "\n[green] ✅ Total matches expected {} [/green]".format(val(expected))
    # )

