import datetime
import json
import os
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
from helpers.utils import val
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()


class RewardsDist:
    def __init__(self, key, amount):

        # If compounding, split rewards between geyser & staking rewards
        if self.has_compounding(key):
            self.toGeyser = amount // 2
            self.toStakingRewards = amount // 2
        else:
            self.toGeyser = amount
            self.toStakingRewards = 0

    def has_compounding(self, key):
        if (
            key == "native.badger"
            or key == "native.uniBadgerWbtc"
            or key == "native.sushiBadgerWbtc"
        ):
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
        for key, value in amounts.items():
            self.amounts[key] = value
            self.distributions[key] = RewardsDist(key, value)
            self.total += value

    def tokensPerDay(self, amount):
        return amount * days(1) / self.duration

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

        # Top up Tree
        # TODO: Make the amount based on what we'll require for the next week
        id = multi.addTx(
            MultisigTxMetadata(
                description="Top up badger tree", operation="Top Up Badger Tree",
            ),
            {
                "to": rewardsEscrow.address,
                "data": rewardsEscrow.transfer.encode_input(badger.token, tree, top_up),
            },
        )

        tx = multi.executeTx(id)

        after = badger.token.balanceOf(tree)
        assert after == before + top_up

        for key, distribution in self.distributions.items():
            console.print(
                "===== Distributions for {} =====".format(key), style="bold yellow"
            )

            # == Distribute to Geyser ==
            geyser = self.badger.getGeyser(key)

            # Approve Geyser as recipient if required
            if not rewardsEscrow.isApproved(geyser):
                id = multi.addTx(
                    MultisigTxMetadata(
                        description="Approve StakingRewards " + key,
                        operation="transfer",
                    ),
                    {
                        "to": rewardsEscrow.address,
                        "data": rewardsEscrow.approveRecipient.encode_input(geyser),
                    },
                )

                multi.executeTx(id)

            numSchedules = geyser.unlockScheduleCount(self.badger.token)
            console.print(
                "Geyser Distribution for {}: {}".format(
                    key, val(distribution.toGeyser)
                ),
                style="yellow",
            )

            id = multi.addTx(
                MultisigTxMetadata(
                    description="Signal unlock schedule for " + key,
                    operation="signalTokenLock",
                ),
                {
                    "to": rewardsEscrow.address,
                    "data": rewardsEscrow.signalTokenLock.encode_input(
                        geyser,
                        self.badger.token,
                        distribution.toGeyser,
                        self.duration,
                        self.start,
                    ),
                },
            )

            multi.executeTx(id)

            # Verify Results
            numSchedulesAfter = geyser.unlockScheduleCount(self.badger.token)

            console.print(
                "Schedule Addition",
                {"numSchedules": numSchedules, "numSchedulesAfter": numSchedulesAfter},
            )

            assert numSchedulesAfter == numSchedules + 1

            unlockSchedules = geyser.getUnlockSchedulesFor(self.badger.token)
            schedule = unlockSchedules[-1]
            print(schedule)
            assert schedule[0] == distribution.toGeyser
            assert schedule[1] == self.end
            assert schedule[2] == self.duration
            assert schedule[3] == self.start

            # == Distribute to StakingRewards, if relevant ==
            if distribution.toStakingRewards > 0:
                stakingRewards = self.badger.getSettRewards(key)
                console.print(
                    "Staking Rewards Distribution for {}: {}".format(
                        key, val(distribution.toStakingRewards)
                    ),
                    style="yellow",
                )

                # Approve if not approved
                if not rewardsEscrow.isApproved(stakingRewards):
                    id = multi.addTx(
                        MultisigTxMetadata(
                            description="Approve StakingRewards " + key,
                            operation="transfer",
                        ),
                        {
                            "to": rewardsEscrow.address,
                            "data": rewardsEscrow.approveRecipient.encode_input(
                                stakingRewards
                            ),
                        },
                    )

                    multi.executeTx(id)

                    assert rewardsEscrow.isApproved(stakingRewards) == True

                # Add tokens if insufficent tokens
                preBal = self.badger.token.balanceOf(stakingRewards)
                if preBal < distribution.toStakingRewards:
                    required = distribution.toStakingRewards - preBal
                    console.print(
                        "⊁ We need to add {} to the {} Badger supply of {} to reach the goal of {} Badger".format(
                            val(required),
                            key,
                            val(preBal),
                            val(distribution.toStakingRewards),
                        ),
                        style="blue",
                    )

                    id = multi.addTx(
                        MultisigTxMetadata(
                            description="Top up tokens for staking rewards " + key,
                            operation="transfer",
                        ),
                        {
                            "to": rewardsEscrow.address,
                            "data": rewardsEscrow.transfer.encode_input(
                                self.badger.token, stakingRewards, required
                            ),
                        },
                    )

                    multi.executeTx(id)

                assert (
                    self.badger.token.balanceOf(stakingRewards)
                    >= distribution.toStakingRewards
                )

                # Modify the rewards duration, if necessary
                if stakingRewards.rewardsDuration() != self.duration:
                    id = multi.addTx(
                        MultisigTxMetadata(
                            description="Modify Staking Rewards duration for " + key,
                            operation="call.notifyRewardAmount",
                        ),
                        {
                            "to": stakingRewards.address,
                            "data": stakingRewards.setRewardsDuration.encode_input(
                                self.duration
                            ),
                        },
                    )
                    tx = multi.executeTx(id)

                # assert stakingRewards.rewardsDuration() == self.duration

                # Notify Rewards Amount
                id = multi.addTx(
                    MultisigTxMetadata(
                        description="Distribute Staking Rewards For " + key,
                        operation="call.notifyRewardAmount",
                    ),
                    {
                        "to": stakingRewards.address,
                        "data": stakingRewards.notifyRewardAmount.encode_input(
                            self.start, distribution.toStakingRewards,
                        ),
                    },
                )

                tx = multi.executeTx(id)
                console.print(tx.call_trace())
                console.print("notify rewards events", tx.events)

                # Verify Results

                rewardsDuration = stakingRewards.rewardsDuration()
                rewardRate = stakingRewards.rewardRate()
                periodFinish = stakingRewards.periodFinish()
                lastUpdate = stakingRewards.lastUpdateTime()

                oldRewardsRate = Wei("50000 ether") // rewardsDuration

                console.log(
                    {
                        "start": to_utc_date(self.start),
                        "end": to_utc_date(self.end),
                        "finish": to_utc_date(periodFinish),
                        "rewardRate": rewardRate,
                        "expectedRewardRate": distribution.toStakingRewards
                        // rewardsDuration,
                        "rewardsRateDiff": rewardRate
                        - distribution.toStakingRewards // rewardsDuration,
                        "oldRewardsRate": oldRewardsRate,
                        "howTheRateChanged": (
                            distribution.toStakingRewards // rewardsDuration
                        )
                        / oldRewardsRate,
                        "howWeExpectedItToChange": Wei("35000 ether")
                        / Wei("50000 ether"),
                        "lastUpdate": to_utc_date(lastUpdate),
                    }
                )

                assert lastUpdate == self.start
                assert rewardsDuration == self.duration
                assert rewardRate == distribution.toStakingRewards // rewardsDuration
                assert periodFinish == self.start + self.duration

                bal = self.badger.token.balanceOf(stakingRewards)
                assert bal >= distribution.toStakingRewards

                if bal > distribution.toStakingRewards * 2:
                    console.print(
                        "[red] Warning: Staking rewards for {} has excessive coins [/red]".format(
                            key
                        )
                    )

                # Harvest the rewards and ensure the amount updated is appropriate
                strategy = self.badger.getStrategy(key)
                keeper = accounts.at(strategy.keeper(), force=True)

                before = strategy.balance()
                chain.sleep(self.start - chain.time() + 2)
                strategy.harvest({"from": keeper})
                after = strategy.balance()

                print({"before": before, "after": after})

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
                    self.badger.rewardsEscrow,
                    encoded,
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
                    "destination",
                    "encoded call",
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

    rest.setStart(to_timestamp(datetime.datetime(2020, 12, 28, 16, 30)))
    rest.setDuration(hours(67.5))

    rest.setAmounts(
        {
            "native.sushiWbtcEth": Wei("34285 ether"),
            "native.sushiBadgerWbtc": Wei("30000 ether"),
        }
    )

    # rest.setAmounts(
    #     {
    #         "native.sushiWbtcEth": Wei("60000 ether"),
    #         "native.sushiBadgerWbtc": Wei("83437.5 ether"),
    #         "native.sbtcCrv": Wei("83437.5 ether"),
    #         "native.tbtcCrv": Wei("83437.5 ether"),
    #         "native.uniBadgerWbtc": Wei("110000 ether"),
    #         "harvest.renCrv": Wei("83437.5 ether"),
    #     }
    # )

    rest.testTransactions()

    rest.printState("Week 4 - Sushi Emerges")

    total = rest.total
    expected = Wei("64285 ether")

    print("overall total ", total)
    print("expected total ", expected)

    assert total == expected

    console.print(
        "\n[green] ✅ Total matches expected {} [/green]".format(val(expected))
    )

