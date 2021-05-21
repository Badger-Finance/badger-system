from brownie import (
    Controller,
    interface,
    chain,
)
from tabulate import tabulate
from rich.console import Console
from helpers.multicall import Multicall
from helpers.registry import registry
from helpers.sett.resolvers import (
    SettCoreResolver,
    StrategyBadgerLpMetaFarmResolver,
    StrategyBasePancakeResolver,
    StrategyHarvestMetaFarmResolver,
    StrategySushiBadgerWbtcResolver,
    StrategyBadgerRewardsResolver,
    StrategySushiLpOptimizerResolver,
    StrategyCurveGaugeResolver,
    StrategyDiggRewardsResolver,
    StrategySushiDiggWbtcLpOptimizerResolver,
    StrategyDiggLpMetaFarmResolver,
    StrategyUniGenericLpResolver,
)
from helpers.utils import digg_shares_to_initial_fragments, val
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
    def __init__(self, data, block, entityKeys):
        self.data = data
        self.block = block
        self.entityKeys = entityKeys

    # ===== Getters =====

    def balances(self, tokenKey, accountKey):
        return self.data["balances." + tokenKey + "." + accountKey]

    def shares(self, tokenKey, accountKey):
        return self.data["shares." + tokenKey + "." + accountKey]

    def get(self, key):
        if key not in self.data.keys():
            raise Exception("Key {} not found in snap data".format(key))
        return self.data[key]

    # ===== Setters =====

    def set(self, key, value):
        self.data[key] = value


class SnapshotManager:
    def __init__(self, badger: BadgerSystem, key):
        self.badger = badger
        self.key = key
        self.sett = badger.getSett(key)
        self.strategy = badger.getStrategy(key)
        self.controller = Controller.at(self.sett.controller())
        self.want = interface.IERC20(self.sett.token())
        self.resolver = self.init_resolver(self.strategy.getName())
        self.snaps = {}
        self.settSnaps = {}
        self.entities = {}

        assert self.want == self.strategy.want()

        # Common entities for all strategies
        self.addEntity("sett", self.sett.address)
        self.addEntity("strategy", self.strategy.address)
        self.addEntity("controller", self.controller.address)
        self.addEntity("governance", self.strategy.governance())
        self.addEntity("governanceRewards", self.controller.rewards())
        self.addEntity("strategist", self.strategy.strategist())

        destinations = self.resolver.get_strategy_destinations()
        for key, dest in destinations.items():
            self.addEntity(key, dest)

    def add_snap_calls(self, entities):
        calls = []
        calls = self.resolver.add_balances_snap(calls, entities)
        calls = self.resolver.add_sett_snap(calls)
        # calls = self.resolver.add_sett_permissions_snap(calls)
        calls = self.resolver.add_strategy_snap(calls, entities=entities)
        return calls

    def snap(self, trackedUsers=None):
        print("snap")
        snapBlock = chain.height
        entities = self.entities

        if trackedUsers:
            for key, user in trackedUsers.items():
                entities[key] = user

        calls = self.add_snap_calls(entities)

        multi = Multicall(calls)
        # multi.printCalls()

        data = multi()
        self.snaps[snapBlock] = Snap(
            data,
            snapBlock,
            [x[0] for x in entities.items()],
        )

        return self.snaps[snapBlock]

    def addEntity(self, key, entity):
        self.entities[key] = entity

    def init_sett_resolver(self, version):
        print("init_sett_resolver", version)
        return SettCoreResolver(self)

    def init_resolver(self, name):
        print("init_resolver", name)
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
        if name == "StrategySushiBadgerWbtc":
            return StrategySushiBadgerWbtcResolver(self)
        if name == "StrategySushiLpOptimizer":
            print("StrategySushiLpOptimizerResolver")
            return StrategySushiLpOptimizerResolver(self)
        if name == "StrategyDiggRewards":
            return StrategyDiggRewardsResolver(self)
        if name == "StrategySushiDiggWbtcLpOptimizer":
            return StrategySushiDiggWbtcLpOptimizerResolver(self)
        if name == "StrategyDiggLpMetaFarm":
            return StrategyDiggLpMetaFarmResolver(self)
        if name == "StrategyPancakeLpOptimizer":
            return StrategyBasePancakeResolver(self)
        if name == "StrategyUniGenericLp":
            return StrategyUniGenericLpResolver(self)
        if name == "StabilizeStrategyDiggV1":
            return StabilizeStrategyDiggV1Resolver(self)

    def settTend(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        tx = self.strategy.tend(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_tend(before, after, tx)

    def settTendViaManager(self, strategy, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        tx = self.badger.badgerRewardsManager.tend(strategy, overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_tend(before, after, tx)

    def settHarvestViaManager(self, strategy, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        tx = self.badger.badgerRewardsManager.harvest(strategy, overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_harvest(before, after, tx)

    def settHarvest(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)
        tx = self.strategy.harvest(overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_harvest(before, after, tx)

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
        tx = self.sett.withdraw(amount, overrides)
        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_withdraw(
                before, after, {"user": user, "amount": amount}, tx
            )

    def settWithdrawAll(self, overrides, confirm=True):
        user = overrides["from"].address
        trackedUsers = {"user": user}
        userBalance = self.sett.balanceOf(user)
        before = self.snap(trackedUsers)
        tx = self.sett.withdraw(userBalance, overrides)
        after = self.snap(trackedUsers)

        if confirm:
            self.resolver.confirm_withdraw(
                before, after, {"user": user, "amount": userBalance}, tx
            )

    def format(self, key, value):
        if type(value) is int:
            if "stakingRewards.staked" or "stakingRewards.earned" in key:
                return val(value)
            # Ether-scaled balances
            # TODO: Handle based on token decimals
            if ".digg" in key and "shares" not in key:
                return val(value, decimals=9)
            if (
                "balance" in key
                or key == "sett.available"
                or key == "sett.pricePerFullShare"
                or key == "sett.totalSupply"
            ):
                return val(value)
            # DIGG Shares
            if "shares" in key or "diggFaucet.earned" in key:
                # We expect to have a known digg instance in the strategy in this case
                name = self.strategy.getName()
                digg = ""

                if name == "StrategyDiggRewards":
                    digg = interface.IDigg(self.strategy.want())
                else:
                    digg = interface.IDigg(self.strategy.digg())

                return digg_shares_to_initial_fragments(digg, value)
        return value

    def diff(self, a, b):
        if type(a) is int and type(b) is int:
            return b - a
        else:
            return "-"

    def printCompare(self, before: Snap, after: Snap):
        # self.printPermissions()
        table = []
        console.print(
            "[green]=== Compare: {} Sett {} -> {} ===[/green]".format(
                self.key, before.block, after.block
            )
        )

        for key, item in before.data.items():

            a = item
            b = after.get(key)

            # Don't add items that don't change
            if a != b:
                table.append(
                    [
                        key,
                        self.format(key, a),
                        self.format(key, b),
                        self.format(key, self.diff(a, b)),
                    ]
                )

        print(
            tabulate(
                table, headers=["metric", "before", "after", "diff"], tablefmt="grid"
            )
        )

    def printPermissions(self):
        # Accounts
        table = []
        console.print("[blue]=== Permissions: {} Sett ===[/blue]".format(self.key))

        table.append(["sett.keeper", self.sett.keeper()])
        table.append(["sett.governance", self.sett.governance()])
        table.append(["sett.strategist", self.sett.strategist()])

        table.append(["---------------", "--------------------"])

        table.append(["strategy.keeper", self.strategy.keeper()])
        table.append(["strategy.governance", self.strategy.governance()])
        table.append(["strategy.strategist", self.strategy.strategist()])
        table.append(["strategy.guardian", self.strategy.guardian()])

        table.append(["---------------", "--------------------"])
        print(tabulate(table, headers=["account", "value"]))

    def printBasics(self, snap: Snap):
        table = []
        console.print("[green]=== Status Report: {} Sett ===[green]".format(self.key))

        table.append(["sett.pricePerFullShare", snap.get("sett.pricePerFullShare")])
        table.append(["strategy.want", snap.balances("want", "strategy")])

        print(tabulate(table, headers=["metric", "value"]))

    def printTable(self, snap: Snap):
        # Numerical Data
        table = []
        console.print("[green]=== Status Report: {} Sett ===[green]".format(self.key))

        for key, item in snap.data.items():
            # Don't display 0 balances:
            if "balances" in key and item == 0:
                continue
            table.append([key, self.format(key, item)])

        table.append(["---------------", "--------------------"])
        print(tabulate(table, headers=["metric", "value"]))
