from tests.conftest import badger
from time import time
from helpers.utils import sec, val
from helpers.time_utils import days, to_days, to_hours, to_utc_date
from assistant.rewards.classes.RewardsLogger import rewardsLogger
from dotmap import DotMap
from rich.console import Console
from tabulate import tabulate
from config.badger_config import badger_config
from statistics import mean
from brownie import *

console = Console()

digg_token = "0x798D1bE841a82a273720CE31c822C61a67a601C3"
badger_token = "0x3472A5A71965499acd81997a54BBA8D852C6E53d"
badger_tree = "0x660802Fc641b154aBA66a62137e71f331B6d787A"
digg = interface.IDigg(digg_token)

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class LinearLogic:
    """
    Linearly increasing rewards between two points. No further increase in rate after end point.
    Time on X axis, must start at 0
    """

    def __init__(self, start, end):
        self.start = Point(start["x"], start["y"])
        self.end = Point(end["x"], end["y"])
        self.slope = (end["y"] - start["y"]) / (end["x"] - start["x"])
        self.intercept = start["y"]
        self.duration = end["x"] - start["x"]

    def y(self, x):
        start = self.start
        end = self.end
        slope = self.slope
        intercept = self.intercept

        if x < start.x:
            assert False  # No negative values

        if x > end.x:
            return end.y

        else:
            sinceStart = x - self.start.x
            y = (slope * sinceStart) + intercept
        return y

    def integral(self, x1, x2):
        y1 = self.y(x1)
        y2 = self.y(x2)

        xDiff = x2 - x1
        yAverage = mean([y2, y1])

        # print("integral", x1, x2, xDiff, y1, y2, yAverage, xDiff * yAverage)

        # console.log("multiplier at start time is {}".format(y1))
        # console.log("multiplier at end time is {}".format(y2))

        return xDiff * yAverage


class BadgerGeyserMock:
    def __init__(self, key):
        self.key = key
        self.events = DotMap()
        self.stakes = DotMap()
        self.totalShareSeconds = 0
        self.users = DotMap()
        self.unlockSchedules = DotMap()
        self.distributionTokens = []
        self.totalDistributions = DotMap()
        self.totalShareSecondsInRange = 0
        self.logic = LinearLogic(
            {"x": 0, "y": badger_config.startMultiplier},
            {"x": days(7 * 8), "y": badger_config.endMultiplier},
        )

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

        # console.log(
        #     "add_unlock_schedule for", str(token), parsedSchedule.toDict(),
        # )

    def get_distributed_for_token_at(self, token, endTime, read=False):
        """
        Get total distribution for token within range, across unlock schedules
        """
        totalToDistribute = 0
        print("get_distributed_for_token_at", token, endTime)
        if token not in self.unlockSchedules:
            return 0
        unlockSchedules = self.unlockSchedules[token]
        index = 0
        for schedule in unlockSchedules:
            if endTime < schedule.startTime:
                toDistribute = 0
                rangeDuration = endTime - schedule.startTime
                if read:
                    console.print(
                        "\n[cyan]Schedule {} for {}: Complete[/cyan]".format(index, self.key)
                    )
            else:
                rangeDuration = endTime - schedule.startTime
                toDistribute = min(
                    schedule.initialTokensLocked,
                    int(
                        schedule.initialTokensLocked
                        * rangeDuration
                        // schedule.duration
                    ),
                )


                # Output if in rewards range, or read flag is on
                if read and (schedule.startTime <= endTime and schedule.endTime >= endTime):
                    console.print(
                        "\n[blue] == Schedule {} for {} == [/blue]".format(index, self.key)
                    )
                    if token == digg_token:
                        console.log(
                            "Total tokens distributed by schedule starting at {} by the end of rewards cycle are {} out of {} total.".format(
                                to_utc_date(schedule.startTime),
                                val(digg.sharesToFragments(toDistribute)),
                                val(digg.sharesToFragments(schedule.initialTokensLocked)),
                            )
                        )
                    else:
                        console.log(
                            "Total tokens distributed by schedule starting at {} by the end of rewards cycle are {} out of {} total.".format(
                                to_utc_date(schedule.startTime),
                                val(toDistribute),
                                val(schedule.initialTokensLocked),
                            )
                        )
                    console.log(
                        "Total duration of schedule elapsed is {} hours out of {} hours, or {}% of total duration.".format(
                            to_hours(rangeDuration), to_hours(schedule.duration), rangeDuration / schedule.duration * 100
                        )
                    )

                    console.log("\n")

            totalToDistribute += toDistribute
            index += 1
        return totalToDistribute

    def calc_token_distributions_in_range(self, startTime, endTime):
        tokenDistributions = DotMap()
        print("calc_token_distributions_in_range", self.distributionTokens)
        for token in self.distributionTokens:
            tokenDistributions[token] = int(
                (
                    self.get_distributed_for_token_at(token, endTime, read=True)
                    - self.get_distributed_for_token_at(token, startTime)
                )
            )
            if token == digg_token:
                console.log(
                "Distributing {} {} tokens for {} geyser in this rewards cycle, out of {} historically locked".format(
                    val(digg.sharesToFragments(tokenDistributions[token])),
                    token,
                    self.key,
                    val(digg.sharesToFragments(self.get_distributed_for_token_at(token, startTime))),
                )
            )
            else:
                console.log(
                "Distributing {} {} tokens for {} geyser in this rewards cycle, out of {} historically locked".format(
                    val(tokenDistributions[token]),
                    token,
                    self.key,
                    val(self.get_distributed_for_token_at(token, startTime)),
                )
            )
            self.totalDistributions[token] = tokenDistributions[token]

        return tokenDistributions

    def calc_token_distributions_at_time(self, endTime):
        """
        For each distribution token tracked by this Geyser, determine how many tokens should be distributed in the specified range.
        This is found by summing the values from all unlockSchedules during the range for this token
        """
        tokenDistributions = DotMap()
        console.print("[cyan]== Calculate Token Distributions ==[/cyan]")
        # console.log(
        #     {
        #         "startTime": startTime,
        #         "endTime": endTime,
        #         "tokens": self.distributionTokens,
        #     }
        # )
        for token in self.distributionTokens:
            tokenDistributions[token] = self.get_distributed_for_token_at(
                token, endTime
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
        userMetadata = {}
        """
        Each user should get their proportional share of each token
        """
        totalShareSecondsUsed = 0
        # console.log("tokenDistributions", tokenDistributions.toDict())

        for user, userData in self.users.items():
            userDistributions[user] = {}
            userMetadata[user] = {}
            # Record total share seconds
            if not "shareSeconds" in userData:
                userMetadata[user]["shareSeconds"] = 0
            else:
                userMetadata[user]["shareSeconds"] = userData.shareSeconds

            # Track Distribution based on seconds in range
            if "shareSecondsInRange" in userData:
                userMetadata[user][
                    "shareSecondsInRange"
                ] = userData.shareSecondsInRange
                totalShareSecondsUsed += userData.shareSecondsInRange
            else:
                userMetadata[user]["shareSecondsInRange"] = 0
            for token, tokenAmount in tokenDistributions.items():
                if "shareSecondsInRange" in userData:
                    userShare = int(
                        tokenAmount
                        * userData.shareSecondsInRange
                        // self.totalShareSecondsInRange
                    )
                    userDistributions[user][token] = userShare

                else: 
                    userDistributions[user][token] = 0

        
        tokenTotals = self.get_token_totals_from_user_dists(userDistributions)

        # Check values vs total for each tokeM
        for token, totalAmount in tokenTotals.items():
            # NOTE The total distributed should be less than or equal to the actual tokens distributed. Rounding dust will go to DAO
            # NOTE The value of the distributed should only be off by a rounding error
            print("duration ", (self.endTime - self.startTime) / 3600)
            print("totalShareSecondsUsed", totalShareSecondsUsed)
            print("self.totalShareSecondsInRange", self.totalShareSecondsInRange)
            print("totalAmount for {}".format(token), totalAmount / 1e18)
            print("self.totalDistributions for {}".format(token), self.totalDistributions[token] / 1e18)
            print("leftover", abs(self.totalDistributions[token] - totalAmount))
            assert abs(self.totalDistributions[token] - totalAmount) < 1e10

        assert totalShareSecondsUsed == self.totalShareSecondsInRange

        return {
            "claims": userDistributions,
            "totals": tokenTotals,
            "metadata": userMetadata,
        }

    def unstake(self, user, unstake):
        # Update share seconds on unstake
        self.process_share_seconds(user, unstake.timestamp)

        # Process unstakes from individual stakes
        toUnstake = int(unstake.amount)
        while toUnstake > 0:
            stake = self.users[user].stakes[-1]

            # This stake won't cover, remove
            if toUnstake >= stake["amount"]:
                self.users[user].stakes.pop()
                toUnstake -= stake["amount"]

            # This stake will cover the unstaked amount, reduce
            else:
                self.users[user].stakes[-1]["amount"] -= toUnstake
                toUnstake = 0

        # Update globals
        self.users[user].total = unstake.userTotal
        self.users[user].lastUpdate = unstake.timestamp

        # console.log("unstake", self.users[user].toDict(), unstake, self.users[user])

    def stake(self, user, stake):
        # Update share seconds for previous stakes on stake
        self.process_share_seconds(user, stake.timestamp)

        # Add Stake
        self.addStake(user, stake)

        # Update Globals
        self.users[user].lastUpdate = stake.timestamp
        self.users[user].total = stake.userTotal

    def addStake(self, user, stake):
        if not self.users[user].stakes:
            self.users[user].stakes = []
        self.users[user].stakes.append(
            {"amount": stake.amount, "stakedAt": stake.stakedAt}
        )

    def calc_end_share_seconds_for(self, user):
        self.process_share_seconds(user, self.endTime)
        self.users[user].lastUpdate = self.endTime

    def calc_end_share_seconds(self):
        """
        Process share seconds after the last action of each user, up to the end time
        If the user took no actions during the claim period, calculate their shareSeconds from their pre-existing stakes
        """

        for user in self.users:
            self.process_share_seconds(user, self.endTime)

    def caclulate_multiplier(self, stake, timestamp):
        start = 0
        end = timestamp - stake["stakedAt"]
        #mult0 = self.logic.y(start)
        mult2 = self.logic.y(end)
        #mean_val = mean([mult0, mult2])
        return mult2

    def calculate_weighted_seconds(self, stake, lastUpdate, timestamp):
        """
        Get "weightedShareSeconds" in range
        """
        # table = []

        start = 0
        previous = lastUpdate - stake["stakedAt"]
        end = timestamp - stake["stakedAt"]

        # print("startY", start, self.logic.y(start))
        # print("lastUpdateY", previous, self.logic.y(previous))
        # print("timestampY", end, self.logic.y(end))

        integral = self.logic.integral(previous, end)
        weighted = int(timestamp - lastUpdate)

        mult0 = self.logic.y(start)
        mult1 = self.logic.y(previous)
        mult2 = self.logic.y(end)

        # table.append(
        #     [
        #         stake["amount"],
        #         stake["stakedAt"],
        #         lastUpdate,
        #         timestamp,
        #         weighted,
        #         integral,
        #         mult0,
        #         mult1,
        #         mult2,
        #     ]
        # )
        # print(
        #     tabulate(
        #         table,
        #         headers=[
        #             "amount",
        #             "stakedAt",
        #             "lastUpdate",
        #             "timestamp",
        #             "weighted",
        #             "integral",
        #             "mult0",
        #             "mult1",
        #             "mult2",
        #         ],
        #     )
        # )
        return int(integral)

    def process_share_seconds(self, user, timestamp):
        data = self.users[user]

        # Return 0 if user has no tokens
        if not "total" in data:
            return 0

        lastUpdate = self.getLastUpdate(user)

        # Either cycle start or last update, whichever comes later
        lastUpdateRangeGated = max(self.startTime, int(lastUpdate))

        timeSinceLastAction = int(timestamp) - int(lastUpdate)
        timeSinceLastActionRangeGated = int(timestamp) - int(lastUpdateRangeGated)

        if timeSinceLastAction == 0:
            return 0

        toAdd = 0
        toAddInRange = 0

        for stake in data.stakes:
            stakeMultiplier = self.caclulate_multiplier(stake, timestamp)

            if not data.stakeMultiplier or data.stakeMultiplier < stakeMultiplier:
                data.stakeMultiplier = stakeMultiplier
            toAdd += stake["amount"] * self.calculate_weighted_seconds(
                stake, lastUpdate, timestamp
            )
            if timestamp > self.startTime:
                toAddInRange += stake["amount"] * self.calculate_weighted_seconds(
                    stake, lastUpdateRangeGated, timestamp
                )
        assert toAdd >= 0

        # If user has share seconds, add
        if "shareSeconds" in data:
            data.shareSeconds += toAdd
            self.totalShareSeconds += toAdd

        # If user has no share seconds, set
        else:
            data.shareSeconds = toAdd
            self.totalShareSeconds += toAdd

        if "shareSecondsInRange" in data:
            data.shareSecondsInRange += toAddInRange
        else:
            data.shareSecondsInRange = toAddInRange
        self.totalShareSecondsInRange += toAddInRange

        self.users[user] = data

    # ===== Getters =====

    def getLastUpdate(self, user):
        """
        Get the last time the specified user took an action
        """
        if not self.users[user].lastUpdate:
            return badger_config.globalStartTime
        return self.users[user].lastUpdate

    def getMockState(self, userDistributions):
        table = []
        numUsers = 0
        numUsersWithClaims = 0
        # console.log("User State", self.users.toDict(), self.totalShareSeconds)
        for user, data in self.users.items():
            numUsers += 1
            rewards = userDistributions["claims"][user][
                badger_token
            ]
            digg_rewards = userDistributions["claims"][user][
                digg_token
            ]
            data.shareSecondsInRange

            sharesPerReward = 0
            if rewards > 0:
                numUsersWithClaims += 1
                sharesPerReward = data.shareSecondsInRange / rewards

            sharesPerDiggReward = 0
            if digg_rewards > 0:
                sharesPerDiggReward = data.shareSecondsInRange / digg_rewards

            table.append(
                [
                    user,
                    val(rewards),
                    digg_rewards,
                    sec(data.shareSecondsInRange),
                    sharesPerReward,
                    sharesPerDiggReward,
                    sec(data.shareSeconds),
                    data.total,
                    data.lastUpdate,
                ]
            )
        print("GEYSER " + self.key)
        # print(
        #     tabulate(
        #         table,
        #         headers=[
        #             "user",
        #             "rewards",
        #             "digg_rewards",
        #             "shareSecondsInRange",
        #             "shareSeconds/reward",
        #             "shareSeconds/digg_reward",
        #             "shareSeconds",
        #             "totalStaked",
        #             "lastUpdate",
        #         ],
        #     )
        # )
        print(
            "Total Badger for Geyser", val(userDistributions["totals"][badger_token])
        )
        print(
            "Total DIGG shares for Geyser", userDistributions["totals"][digg_token]
        )
        print(
            "Total DIGG tokens for Geyser", digg.sharesToFragments(userDistributions["totals"][digg_token])
        )
        print(
            "Total Users", numUsers
        )
        print(
            "Total Users With Claims", numUsersWithClaims

        )
        return {
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d":userDistributions["totals"][badger_token],
            "0x798D1bE841a82a273720CE31c822C61a67a601C3":userDistributions["totals"][digg_token]
        }

        # console.log('printState')
