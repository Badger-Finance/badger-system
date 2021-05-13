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
from helpers.utils import initial_fragments_to_current_fragments, val
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.token_utils import asset_to_address

console = Console()
pretty.install()


class StakingRewardsDistributor:
    """
    Generate appropriate staking rewards distributions transaction given a set of emissions
    """

    def __init__(self, badger, multi, key, distributions, start=0, duration=0, end=0):
        # == Distribute to Geyser ==
        geyser = badger.getGeyser(key)
        rewardsEscrow = badger.rewardsEscrow

        self.start = start
        self.duration = duration
        self.end = end

        multi = GnosisSafe(badger.devMultisig)
        for asset, dist in distributions.items():
            token = asset_to_address(asset)
            self.validate_staking_rewards_emission(key, asset)

            stakingRewards = badger.getSettRewards(key)
            console.print(
                "Staking Rewards Distribution for asset {} on {}: {}".format(
                    asset, key, val(dist)
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
            preBal = badger.token.balanceOf(stakingRewards)
            print("PreBalance", val(preBal))

            if preBal < dist:
                required = dist - preBal
                console.print(
                    "⊁ We need to add {} to the {} Badger supply of {} to reach the goal of {} Badger".format(
                        val(required), key, val(preBal), val(dist),
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
                            badger.token, stakingRewards, required
                        ),
                    },
                )

                multi.executeTx(id)

            assert badger.token.balanceOf(stakingRewards) >= dist

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
                        self.start, dist,
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
                    "expectedRewardRate": dist // rewardsDuration,
                    "rewardsRateDiff": rewardRate - dist // rewardsDuration,
                    "oldRewardsRate": oldRewardsRate,
                    "howTheRateChanged": (dist // rewardsDuration) / oldRewardsRate,
                    "howWeExpectedItToChange": Wei("35000 ether") / Wei("50000 ether"),
                    "lastUpdate": to_utc_date(lastUpdate),
                }
            )

            assert lastUpdate == self.start
            assert rewardsDuration == self.duration
            assert rewardRate == dist // rewardsDuration
            assert periodFinish == self.start + self.duration

            bal = badger.token.balanceOf(stakingRewards)
            assert bal >= dist

            if bal > dist * 2:
                console.print(
                    "[red] Warning: Staking rewards for {} has excessive coins [/red]".format(
                        key
                    )
                )

            # Harvest the rewards and ensure the amount updated is appropriate
            strategy = badger.getStrategy(key)
            keeper = accounts.at(strategy.keeper(), force=True)

            before = strategy.balance()
            chain.sleep(self.start - chain.time() + 2)
            strategy.harvest({"from": keeper})
            after = strategy.balance()

            print({"before": before, "after": after})

    def validate_staking_rewards_emission(self, key, asset):
        """
        Ensure the specified geyser is capable of distributing the given asset
        """
        if (
            key == "native.digg"
            or key == "native.uniDiggWbtc"
            or key == "native.sushiDiggWbtc"
        ):
            if asset == "digg":
                return True
        if (
            key == "native.badger"
            or key == "native.uniBadgerWbtc"
            or key == "native.sushiBadgerWbtc"
        ):
            if asset == "badger":
                return True
        else:
            return False
