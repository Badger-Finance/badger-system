from helpers.sett.resolvers.StrategyCurveGaugeResolver import StrategyCurveGaugeResolver
from helpers.sett.resolvers.StrategyBadgerLpMetaFarmResolver import (
    StrategyBadgerLpMetaFarmResolver,
)
from brownie import *
from helpers.constants import *
from helpers.multicall import Call, Multicall, as_wei, func
from helpers.registry import registry
from helpers.sett.resolvers.StrategyHarvestMetaFarmResolver import (
    StrategyHarvestMetaFarmResolver,
)
from helpers.sett.resolvers.StrategyBadgerRewardsResolver import (
    StrategyBadgerRewardsResolver,
)
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem

console = Console()


def get_expected_strategy_deposit_location(badger: BadgerSystem, id):
    if id == "native.badger":
        # Rewards Staking
        return badger.getSettRewards("native.badger")
    if id == "native.uniBadgerWbtc":
        # Rewards Staking
        return badger.getSettRewards("native.uniBadgerWbtc")
    if id == "native.renCrv":
        # CRV Gauge
        return registry.curve.pools.renCrv.gauge
    if id == "native.sbtcCrv":
        # CRV Gauge
        return registry.curve.pools.sbtcCrv.gauge
    if id == "native.tbtcCrv":
        # CRV Gauge
        return registry.curve.pools.tbtcCrv.gauge
    if id == "harvest.renCrv":
        # Harvest Vault
        return registry.harvest.vaults.renCrv


def is_curve_gauge_variant(name):
    return (
        name == "StrategyCurveGaugeRenBtcCrv"
        or name == "StrategyCurveGaugeSbtcCrv"
        or name == "StrategyCurveGaugeTbtcCrv"
        or name == "StrategyCurveGaugex"
    )


class Snap:
    def __init__(self, data):
        self.data = data

    # ===== Getters =====

    def balances(self, tokenKey, accountKey):
        return self.data["balances." + tokenKey + "." + accountKey]

    def sumBalances(self, tokenKey, accountKeys):
        total = 0
        for accountKey in accountKeys:
            total += self.data["balances." + tokenKey + "." + accountKey]
        return total

    def get(self, key):

        if not key in self.data.keys():
            assert False
        return self.data[key]

    # ===== Setters =====

    def set(self, key, value):
        self.data[key] = value


class SnapshotManager:
    def __init__(self, badger: BadgerSystem, key):
        print("Create snapshot manager ", key)
        self.badger = badger
        self.key = key
        self.sett = badger.getSett(key)
        self.strategy = badger.getStrategy(key)
        self.controller = Controller.at(self.sett.controller())
        self.want = interface.IERC20(self.sett.token())
        self.resolver = self.init_resolver(self.strategy.getName())
        self.snaps = {}
        self.entities = {}

        assert self.want == self.strategy.want()

        self.addEntity("sett", self.sett.address)
        self.addEntity("strategy", self.strategy.address)
        self.addEntity("controller", self.controller.address)
        self.addEntity("governance", self.strategy.governance())
        self.addEntity("governanceRewards", self.controller.rewards())
        self.addEntity("strategist", self.strategy.strategist())

        destinations = self.resolver.get_strategy_destinations()
        for key, dest in destinations.items():
            self.addEntity(key, dest)

    def snap(self, trackedUsers):
        snapBlock = chain.height
        entities = self.entities

        for key, user in trackedUsers.items():
            entities[key] = user

        calls = []
        calls = self.resolver.add_balances_snap(calls, entities)
        calls = self.resolver.add_sett_snap(calls)
        calls = self.resolver.add_strategy_snap(calls)

        multi = Multicall(calls)

        # for call in calls:
        #     print(call.target, call.function, call.args)

        data = multi()
        self.snaps[snapBlock] = Snap(data)

        return self.snaps[snapBlock]

    def addEntity(self, key, entity):
        self.entities[key] = entity

    def init_resolver(self, name):
        console.log("init_resolver", name)
        if name == "StrategyHarvestMetaFarm":
            return StrategyHarvestMetaFarmResolver(self)
        if name == "StrategyBadgerRewards":
            return StrategyBadgerRewardsResolver(self)
        if name == "StrategyBadgerLpMetaFarm":
            return StrategyBadgerLpMetaFarmResolver(self)
        if is_curve_gauge_variant(name):
            return StrategyCurveGaugeResolver(self)
        if name == "StrategyCurveGauge":
            return StrategyCurveGaugeResolver(self)

    def settTend(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        self.sett.tend(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_tend(before, after, {"user": user})

    def settHarvest(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        self.sett.harvest(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_harvest(before, after, {"user": user})

    def settDeposit(self, amount, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        self.sett.deposit(amount, overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_deposit(
                before, after, {"user": user, "amount": amount}
            )

    def settDepositAll(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        userBalance = self.want.balanceOf(user)
        before = self.snap(trackedUsers)
        self.sett.depositAll(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_deposit(
                before, after, {"user": user, "amount": userBalance}
            )

    def settEarn(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        self.sett.earn(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_earn(before, after, {"user": user})

    def settWithdraw(self, amount, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        self.sett.withdraw(amount, overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_withdraw(
                before, after, {"user": user, "amount": amount}
            )

    def settWithdrawAll(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        userBalance = self.sett.balanceOf(user)
        before = self.snap(trackedUsers)
        self.sett.withdraw(userBalance, overrides)
        after = self.snap(trackedUsers)

        if confirm:
            self.resolver.confirm_withdraw(
                before, after, {"user": user, "amount": userBalance}
            )
