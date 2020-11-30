import json
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from functools import partial, wraps
from itertools import zip_longest
from os import times
from pathlib import Path

import toml
from brownie import MerkleDistributor, Wei, accounts, interface, rpc, web3
from brownie.utils import color
from click import secho
from dotmap import DotMap
from eth_abi import decode_single, encode_single
from eth_abi.packed import encode_abi_packed
from eth_utils import encode_hex
from helpers.constants import AddressZero
from rich.console import Console
from toolz import valfilter, valmap
from tqdm import tqdm, trange

console = Console()


class BadgerGeyserMock:
    def __init__(self):
        self.events = DotMap()
        self.stakes = DotMap()
        self.totalShareSeconds = 0
        self.users = DotMap()
        self.unlockSchedules = DotMap()
        self.distributionTokens = []
        self.totalDistributions = DotMap()

    # ===== Setters =====

    def set_current_period(self, startTime, endTime):
        self.startTime = startTime
        self.endTime = endTime

    def set_stakes():
        """
        Set the current stakes for a user based on historical events
        """
        return False

    def add_distribution_token(self, token):
        self.distributionTokens.append(token)

    def add_unlock_schedule(self, token, unlockSchedule):
        if not self.unlockSchedules[str(token)]:
            self.unlockSchedules[str(token)] = []

        parsedSchedule = DotMap(
            initialTokensLocked=unlockSchedule[0],
            endTime=unlockSchedule[1],
            duration=unlockSchedule[2],
            startTime=unlockSchedule[3],
        )

        self.unlockSchedules[str(token)].append(parsedSchedule)

        console.log(
            "add_unlock_schedule for", str(token), parsedSchedule.toDict(),
        )

    def get_distributed_for_token(self, token, startTime, endTime):
        """
        Get total distribution for token within range, across unlock schedules
        """
        totalToDistribute = 0

        unlockSchedules = self.unlockSchedules[token]
        for schedule in unlockSchedules:
            rangeDuration = endTime - startTime
            toDistribute = min(
                schedule.initialTokensLocked,
                int(schedule.initialTokensLocked * rangeDuration // schedule.duration),
            )

            totalToDistribute += toDistribute
        return totalToDistribute

    def calc_token_distributions_in_range(self, startTime, endTime):
        """
        For each distribution token tracked by this Geyser, determine how many tokens should be distributed in the specified range.
        This is found by summing the values from all unlockSchedules during the range for this token
        """
        tokenDistributions = DotMap()
        console.print("[cyan]== Calculate Token Distributions ==[/cyan]")
        console.log(
            {
                "startTime": startTime,
                "endTime": endTime,
                "tokens": self.distributionTokens,
            }
        )
        for token in self.distributionTokens:
            tokenDistributions[token] = self.get_distributed_for_token(
                token, startTime, endTime
            )
            self.totalDistributions[token] = tokenDistributions[token]

        return tokenDistributions

    def get_token_totals_from_user_dists(self, userDistributions):
        tokenTotals = {}
        for user, userData in userDistributions.items():
            for token, tokenAmount in userData.items():
                if token in tokenTotals:
                    tokenTotals[token] += tokenAmount
                else:
                    tokenTotals[token] = tokenAmount
        return tokenTotals

    def calc_user_distributions(self, tokenDistributions):
        userDistributions = {}
        """
        Each user should get their proportional share of each token
        """
        totalShareSecondsUsed = 0
        console.log("tokenDistributions", tokenDistributions.toDict())

        for user, userData in self.users.items():
            userDistributions[user] = {}
            console.log("user, userData", user, userData.toDict())
            for token, tokenAmount in tokenDistributions.items():
                if not "shareSeconds" in userData:
                    userDistributions[user][token] = 0
                else:
                    console.log(
                        "calc_user_distributions",
                        {
                            "user": user,
                            "userData": userData,
                            "self.totalShareSeconds": self.totalShareSeconds,
                            "userData.shareSeconds": userData.shareSeconds,
                            "token": tokenAmount,
                            "tokenAmount": tokenAmount,
                        },
                    )
                    console.log(
                        "user share seconds",
                        int(
                            tokenAmount
                            * userData.shareSeconds
                            // self.totalShareSeconds
                        ),
                    )
                    userShare = int(
                        tokenAmount * userData.shareSeconds // self.totalShareSeconds
                    )
                    userDistributions[user][token] = userShare
                    totalShareSecondsUsed += userData.shareSeconds

        console.log("Confirm User Distributions", userDistributions)

        console.log(
            "Share Seconds Assertion",
            totalShareSecondsUsed / 1e18,
            self.totalShareSeconds / 1e18,
            abs(totalShareSecondsUsed - self.totalShareSeconds) / 1e18,
        )
        assert totalShareSecondsUsed == self.totalShareSeconds

        tokenTotals = self.get_token_totals_from_user_dists(userDistributions)

        console.log("Token Totals", tokenTotals, self.totalDistributions.toDict())

        # Check values vs total for each token
        for token, totalAmount in tokenTotals.items():
            print(
                totalAmount,
                self.totalDistributions[token],
                abs(self.totalDistributions[token] - totalAmount),
            )
            # NOTE The total distributed should be less than or equal to the actual tokens distributed. Rounding dust will go to DAO
            # NOTE The value of the distributed should only be off by a rounding error
            assert totalAmount <= self.totalDistributions[token]
            assert abs(self.totalDistributions[token] - totalAmount) < 10

        return {"claims": userDistributions, "totals": tokenTotals}

    def unstake(self, user, unstake, trackShareSeconds=True):
        # Update share seconds on unstake
        if trackShareSeconds:
            self.process_share_seconds(user, unstake.timestamp)
            self.users[user].unstakedDuringPeriod = True
            self.users[user].actedDuringPeriod = True

        # Process unstakes from individual stakes
        # TODO:
        toUnstake = unstake.amount
        while toUnstake > 0:
            console.log(
                "unstaking",
                {"toUnstake": toUnstake, "unstake.amount": unstake.amount},
                self.users[user].stakes,
            )
            stake = self.users[user].stakes[-1]
            # TODO: Start at the end
            if toUnstake >= stake["amount"]:
                self.users[user].stakes.pop()
                toUnstake -= stake["amount"]
            else:
                toUnstake -= self.users[user].stakes[-1]["amount"]
                self.users[user].stakes[-1]["amount"] -= toUnstake

        # Update globals
        self.users[user].total = unstake.userTotal
        self.users[user].lastUpdate = unstake.timestamp

        console.log("unstake", self.users[user].toDict(), unstake, self.users[user])

    def stake(self, user, stake, trackShareSeconds=True):
        # Update share seconds for previous stakes on stake
        if trackShareSeconds:
            self.process_share_seconds(user, stake.timestamp)
            self.users[user].actedDuringPeriod = True

        # Add Stake
        self.addStake(user, stake)

        # Update Globals
        self.users[user].lastUpdate = stake.timestamp
        self.users[user].total = stake.userTotal

        console.log("stake", self.users[user].toDict(), stake, self.users[user])

    def addStake(self, user, stake):
        if not self.users[user].stakes:
            self.users[user].stakes = []
        self.users[user].stakes.append(
            {"amount": stake.amount, "stakedAt": stake.stakedAt}
        )

    def calc_end_share_seconds(self):
        """
        Process share seconds after the last action of each user, up to the end time
        If the user took no actions during the claim period, calculate their shareSeconds from their pre-existing stakes
        """

        for user in self.users:
            lastUpdate = self.getLastUpdate(user)
            acted = self.didUserAct(user)
            console.log(
                "calc_end_share_seconds",
                user,
                acted,
                lastUpdate,
                self.endTime,
                acted and lastUpdate < self.endTime,
            )

            # If the user acted during the claim period and did not calculate share seconds up to end time
            if acted and lastUpdate < self.endTime:
                self.process_share_seconds(user, self.endTime)

    def process_share_seconds(self, user, end):
        """
        Calculate how many shareSeconds to add to the user
        - How much time has past since the users' stake was calculated?
        - What is their current total staked?
        shareSecondsToAdd = timeSince * totalStaked

        (If the user has no share seconds, set)
        (If the user has shares seconds, add)
        """

        # Return 0 if user has no tokens
        if not self.users[user].total:
            return 0

        # Get time since last update
        lastUpdate = self.getLastUpdate(user)
        timeSinceLastAction = end - lastUpdate
        console.log("timeSinceLastAction", end, lastUpdate, timeSinceLastAction)

        toAdd = self.users[user].total * timeSinceLastAction
        # If user has share seconds, add
        if "shareSeconds" in self.users[user]:
            self.users[user].shareSeconds += toAdd
            self.totalShareSeconds += toAdd

        # If user has no share seconds, set
        # NOTE This should only be the case if the user took no actions during the claim period. In this case their stake is the same as the pre-snapshot stake * total claim period time
        else:
            self.users[user].shareSeconds = toAdd
            self.totalShareSeconds += toAdd

        console.log(
            "processed_share_seconds",
            self.users[user].toDict(),
            end,
            timeSinceLastAction,
        )

    # ===== Getters =====

    def didUserAct(self, user):
        if "actedDuringPeriod" in self.users[user]:
            return self.users[user].actedDuringPeriod
        else:
            return False

    def getLastUpdate(self, user):
        """
        Get the last time the specified user took an action
        """
        if not self.users[user].lastUpdate:
            return 0
        return self.users[user].lastUpdate

    def printState(self):
        console.log("User State", self.users.toDict(), self.totalShareSeconds)

    def getUserWeights(self):
        """
        User -> shareSeconds
        """
        weights = DotMap()
        for user, userData in self.users.items():
            if "shareSeconds" in userData:
                weights[user] = userData.shareSeconds
            else:
                weights[user] = 0
        console.log("weights", weights.toDict())
        return weights

