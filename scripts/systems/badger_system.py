import json
from scripts.systems.uniswap_system import UniswapSystem, connect_uniswap
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.time_utils import daysToSeconds
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from brownie import *
from helpers.constants import AddressZero, EmptyBytes32
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, sett_config, badger_total_supply
from scripts.systems.sett_system import (
    deploy_controller,
    deploy_sett,
    deploy_sett_system,
    deploy_strategy,
)


def deploy_geyser(badger, stakingToken):
    pool_input = DotMap(
        stakingToken=stakingToken.address,
        initialDistributionToken=badger.token.address,
    )

    return deploy_proxy(
        "BadgerGeyser",
        BadgerGeyser.abi,
        badger.logic.BadgerGeyser.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerGeyser.initialize.encode_input(
            pool_input["stakingToken"],
            pool_input["initialDistributionToken"],
            badger_config.geyserParams.badgerDistributionStart,
            badger.devMultisig.address,
            badger.rewardsEscrow.address,
        ),
        badger.deployer,
    )


def print_to_file(badger, path):
    system = {
        "deployer": badger.deployer.address,
        "guardian": badger.guardian.address,
        "keeper": badger.keeper.address,
        "devProxyAdmin": badger.devProxyAdmin.address,
        "daoProxyAdmin": badger.daoProxyAdmin.address,
        "devMultisig": badger.devMultisig.address,
        "token": badger.token.address,
        "logic": {},
        "dao": {},
        "sett_system": {},
        "uniBadgerWbtcLp": badger.pair.address,
        "daoBadgerTimelock": badger.daoBadgerTimelock.address,
        "teamVesting": badger.teamVesting.address,
        "badgerHunt": badger.badgerHunt.address,
        "badgerTree": badger.badgerTree.address,
    }

    print(badger.dao)

    # == DAO ==
    for key, value in badger.dao.items():
        system["dao"][key] = value.address

    # == Pools ==
    system["geysers"] = {}

    for key, value in badger.geysers.items():
        system["geysers"][key] = value.address

    for key, value in badger.logic.items():
        system["logic"][key] = value.address

    # == Sett ==
    system["sett_system"]["controllers"] = {}
    system["sett_system"]["vaults"] = {}
    system["sett_system"]["strategies"] = {}
    system["sett_system"]["rewards"] = {}

    for key, value in badger.sett_system.controllers.items():
        system["sett_system"]["controllers"][key] = value.address

    for key, value in badger.sett_system.vaults.items():
        system["sett_system"]["vaults"][key] = value.address

    for key, value in badger.sett_system.strategies.items():
        system["sett_system"]["strategies"][key] = value.address

    for key, value in badger.sett_system.rewards.items():
        system["sett_system"]["rewards"][key] = value.address

    with open(path, "w") as outfile:
        json.dump(system, outfile)


def deploy_badger(systems, deployer):
    """
    Deploy fresh badger system
    """
    badger = BadgerSystem(badger_config, systems)

    # TODO: Replace with prod values
    badger.deployer = deployer
    badger.keeper = deployer
    badger.guardian = deployer

    badger.devProxyAdmin = deploy_proxy_admin()
    badger.daoProxyAdmin = deploy_proxy_admin()
    badger.proxyAdmin = badger.devProxyAdmin

    # Deploy Dev Multisig (Later Connect)
    multisigParams = badger_config["devMultisigParams"]
    multisigParams.owners = [deployer.address]

    print("Deploy Dev Multisig")
    badger.devMultisig = systems.gnosis_safe.deployGnosisSafe(multisigParams, deployer)

    print("Connect to DAO")
    badger.dao = DotMap(
        token=Contract.from_abi(
            "MiniMeToken",
            dao_config.token,
            registry.aragon.artifacts.MiniMeToken["abi"],
            deployer,
        ),
        kernel=Contract.from_abi(
            "Agent", dao_config.kernel, registry.aragon.artifacts.Agent["abi"], deployer
        ),
        agent=Contract.from_abi(
            "Agent", dao_config.agent, registry.aragon.artifacts.Agent["abi"], deployer
        ),
    )

    # badger.dao = systems.aragon.deployCompanyDao(daoParams, deployer)

    # Alias for badger token
    badger.token = badger.dao.token

    # Requires ganache --unlock for initial owner
    badger.token.transfer(
        deployer, badger_total_supply, {"from": dao_config.initialOwner}
    )

    # Deploy necessary logic contracts
    print("Deploy Logic Contracts")
    badger.logic = DotMap(
        SmartVesting=SmartVesting.deploy({"from": deployer}),
        SmartTimelock=SmartTimelock.deploy({"from": deployer}),
        RewardsEscrow=RewardsEscrow.deploy({"from": deployer}),
        BadgerGeyser=BadgerGeyser.deploy({"from": deployer}),
        BadgerTree=BadgerTree.deploy({"from": deployer}),
        BadgerHunt=BadgerHunt.deploy({"from": deployer}),
        SimpleTimelock=SimpleTimelock.deploy({"from": deployer}),
    )

    # Deploy Rewards
    guardian = deployer
    updater = deployer

    print("Deploy Rewards Infrastructure")
    # TODO: Should be owned by devMultisig
    badger.rewardsEscrow = deploy_proxy(
        "RewardsEscrow",
        RewardsEscrow.abi,
        badger.logic.RewardsEscrow.address,
        badger.devProxyAdmin.address,
        badger.logic.RewardsEscrow.initialize.encode_input(deployer),
        deployer,
    )

    badger.badgerTree = deploy_proxy(
        "BadgerTree",
        BadgerTree.abi,
        badger.logic.BadgerTree.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerTree.initialize.encode_input(
            badger.devMultisig, updater, guardian
        ),
        deployer,
    )

    # Deploy Sett Subsystem
    print("Deploy Sett")
    badger.sett = deploy_sett_system(badger, deployer)

    # Deploy timelocks & vesting
    # DAO Badger Vesting
    print("Deploy Locks & Vesting")
    badger.daoBadgerTimelock = deploy_proxy(
        "SimpleTimelock",
        SimpleTimelock.abi,
        badger.logic.SimpleTimelock.address,
        AddressZero,
        badger.logic.SimpleTimelock.initialize.encode_input(
            badger.token, badger.dao.agent, badger_config.tokenLockParams.lockDuration
        ),
        badger.deployer,
    )

    # Team Badger Vesting
    badger.teamVesting = deploy_proxy(
        "SmartVesting",
        SmartVesting.abi,
        badger.logic.SmartVesting.address,
        AddressZero,
        badger.logic.SmartVesting.initialize.encode_input(
            badger.token,
            badger.devMultisig,
            badger.dao.agent,
            badger_config.teamVestingParams.startTime,
            badger_config.teamVestingParams.cliffDuration,
            badger_config.teamVestingParams.totalDuration,
        ),
        badger.deployer,
    )

    print("Deploy Rewards Pools")
    badger.pools = DotMap(
        sett=DotMap(native=DotMap(), pickle=DotMap(), harvest=DotMap())
    )

    # Deploy staking pools
    badger.pools.sett.native.renCrv = deploy_geyser(badger, badger.sett.native.renCrv)
    badger.pools.sett.native.sbtcCrv = deploy_geyser(badger, badger.sett.native.sbtcCrv)
    badger.pools.sett.native.tbtcCrv = deploy_geyser(badger, badger.sett.native.tbtcCrv)
    badger.pools.sett.native.badger = deploy_geyser(badger, badger.sett.native.badger)

    badger.pools.sett.pickle.renCrv = deploy_geyser(badger, badger.sett.pickle.renCrv)
    badger.pools.sett.harvest.renCrv = deploy_geyser(badger, badger.sett.harvest.renCrv)

    print("Deploy Airdrop")
    # Deploy Hunt
    badger.badgerHunt = deploy_proxy(
        "BadgerHunt",
        BadgerHunt.abi,
        badger.logic.BadgerHunt.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerHunt.initialize.encode_input(
            badger.token,
            EmptyBytes32,
            daysToSeconds(1),
            2000,
            badger_config.huntParams.startTime,
            daysToSeconds(1),
            badger.rewardsEscrow,
        ),
        badger.deployer,
    )

    print("Printing contract addresses to local.json")
    print_to_file(badger, "local.json")

    # Upgradeable Contracts
    badger.contracts = [
        badger.badgerTree,
        badger.badgerHunt,
        badger.rewardsEscrow,
        badger.sett.native.controller,
        badger.sett.harvest.controller,
        badger.sett.pickle.controller,
        badger.sett.native.badger,
        badger.sett.native.renCrv,
        badger.sett.native.sBtcCrv,
        badger.sett.native.tBtcCrv,
        badger.sett.harvest.renCrv,
        badger.sett.pickle.renCrv,
        badger.sett.native.strategies.badger,
        badger.sett.native.strategies.renCrv,
        badger.sett.native.strategies.sBtcCrv,
        badger.sett.native.strategies.tBtcCrv,
        badger.sett.harvest.strategies.renCrv,
        badger.sett.pickle.strategies.renCrv,
        badger.sett.rewards.badger,
        badger.teamVesting,
        badger.daoBadgerTimelock,
        badger.pools.sett.native.renCrv,
        badger.pools.sett.native.sBtcCrv,
        badger.pools.sett.native.tBtcCrv,
        badger.pools.sett.harvest.renCrv,
        badger.pools.sett.pickle.renCrv,
    ]

    return badger


def connect_badger(registry):
    """
    Connect to existing badger deployment
    """
    assert False


class BadgerSystem:
    def __init__(self, config, systems, deployer):
        self.config = config
        self.systems = systems
        self.contracts_static = []
        self.contracts_upgradeable = []

        # TODO: Replace with prod values
        self.deployer = deployer
        self.keeper = deployer
        self.guardian = deployer

        self.devProxyAdmin = deploy_proxy_admin()
        self.daoProxyAdmin = deploy_proxy_admin()
        self.proxyAdmin = self.devProxyAdmin
        self.logic = DotMap()
        self.sett_system = DotMap(
            controllers=DotMap(), vaults=DotMap(), strategies=DotMap(), rewards=DotMap()
        )
        self.geysers = DotMap()

        self.connect_dao()
        self.connect_multisig()
        self.connect_uniswap()

        self.globalStartTime = badger_config.globalStartTime
        print("globalStartTime", self.globalStartTime)

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, contract):
        self.contracts_upgradeable.append(contract)

    # ===== Contract Connectors =====
    def connect_dao(self):
        deployer = self.deployer
        self.dao = DotMap(
            token=Contract.from_abi(
                "MiniMeToken",
                badger_config.dao.token,
                registry.aragon.artifacts.MiniMeToken["abi"],
                deployer,
            ),
            kernel=Contract.from_abi(
                "Agent",
                badger_config.dao.kernel,
                registry.aragon.artifacts.Agent["abi"],
                deployer,
            ),
            agent=Contract.from_abi(
                "Agent",
                badger_config.dao.agent,
                registry.aragon.artifacts.Agent["abi"],
                deployer,
            ),
        )

        self.token = self.dao.token

    def connect_multisig(self):
        deployer = self.deployer

        multisigParams = badger_config["devMultisigParams"]
        multisigParams.owners = [deployer.address]

        print("Deploy Dev Multisig")
        self.devMultisig = connect_gnosis_safe(badger_config.multisig.address)
        self.updater = deployer
        self.guardian = deployer

    def connect_uniswap(self):
        self.uniswap = UniswapSystem()

    # ===== Deployers =====

    def add_controller(self, id):
        deployer = self.deployer
        controller = deploy_controller(self, deployer)
        self.sett_system.controllers[id] = controller
        self.track_contract_upgradeable(controller)
        return controller

    def deploy_core_logic(self):
        deployer = self.deployer
        self.logic = DotMap(
            SmartVesting=SmartVesting.deploy({"from": deployer}),
            SmartTimelock=SmartTimelock.deploy({"from": deployer}),
            RewardsEscrow=RewardsEscrow.deploy({"from": deployer}),
            BadgerGeyser=BadgerGeyser.deploy({"from": deployer}),
            BadgerTree=BadgerTree.deploy({"from": deployer}),
            BadgerHunt=BadgerHunt.deploy({"from": deployer}),
            SimpleTimelock=SimpleTimelock.deploy({"from": deployer}),
        )

    def deploy_sett_core_logic(self):
        deployer = self.deployer
        self.logic.Controller = Controller.deploy({"from": deployer})
        self.logic.Sett = Sett.deploy({"from": deployer})
        self.logic.StakingRewards = StakingRewards.deploy({"from": deployer})

    def deploy_sett_strategy_logic(self):
        deployer = self.deployer
        self.logic.StrategyBadgerRewards = StrategyBadgerRewards.deploy(
            {"from": deployer}
        )
        self.logic.StrategyBadgerLpMetaFarm = StrategyBadgerLpMetaFarm.deploy(
            {"from": deployer}
        )
        self.logic.StrategyHarvestMetaFarm = StrategyHarvestMetaFarm.deploy(
            {"from": deployer}
        )
        self.logic.StrategyPickleMetaFarm = StrategyPickleMetaFarm.deploy(
            {"from": deployer}
        )

        self.logic.StrategyCurveGaugeTbtcCrv = StrategyCurveGaugeTbtcCrv.deploy(
            {"from": deployer}
        )
        self.logic.StrategyCurveGaugeSbtcCrv = StrategyCurveGaugeSbtcCrv.deploy(
            {"from": deployer}
        )
        self.logic.StrategyCurveGaugeRenBtcCrv = StrategyCurveGaugeRenBtcCrv.deploy(
            {"from": deployer}
        )

    def deploy_rewards_escrow(self):
        deployer = self.deployer
        self.rewardsEscrow = deploy_proxy(
            "RewardsEscrow",
            RewardsEscrow.abi,
            self.logic.RewardsEscrow.address,
            self.devProxyAdmin.address,
            self.logic.RewardsEscrow.initialize.encode_input(deployer),
            deployer,
        )
        self.track_contract_upgradeable(self.rewardsEscrow)

    def deploy_badger_tree(self):
        deployer = self.deployer
        self.badgerTree = deploy_proxy(
            "BadgerTree",
            BadgerTree.abi,
            self.logic.BadgerTree.address,
            self.devProxyAdmin.address,
            self.logic.BadgerTree.initialize.encode_input(
                self.devMultisig, self.updater, self.guardian
            ),
            deployer,
        )
        self.track_contract_upgradeable(self.badgerTree)

    def deploy_badger_hunt(self):
        deployer = self.deployer
        self.badgerHunt = deploy_proxy(
            "BadgerHunt",
            BadgerHunt.abi,
            self.logic.BadgerHunt.address,
            self.devProxyAdmin.address,
            self.logic.BadgerHunt.initialize.encode_input(
                self.token,
                EmptyBytes32,
                daysToSeconds(1),
                2000,
                badger_config.huntParams.startTime,
                daysToSeconds(1),
                self.rewardsEscrow,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.badgerHunt)

    def deploy_dao_badger_timelock(self):
        deployer = self.deployer
        self.daoBadgerTimelock = deploy_proxy(
            "SimpleTimelock",
            SimpleTimelock.abi,
            self.logic.SimpleTimelock.address,
            AddressZero,
            self.logic.SimpleTimelock.initialize.encode_input(
                self.token, self.dao.agent, badger_config.tokenLockParams.lockDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.daoBadgerTimelock)

    def deploy_dao_digg_timelock(self):
        deployer = self.deployer

    def deploy_team_vesting(self):
        deployer = self.deployer

        self.teamVesting = deploy_proxy(
            "SmartVesting",
            SmartVesting.abi,
            self.logic.SmartVesting.address,
            AddressZero,
            self.logic.SmartVesting.initialize.encode_input(
                self.token,
                self.devMultisig,
                self.dao.agent,
                badger_config.teamVestingParams.startTime,
                badger_config.teamVestingParams.cliffDuration,
                badger_config.teamVestingParams.totalDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.teamVesting)

    def add_logic(self, name, BrownieArtifact):
        deployer = self.deployer
        self.logic[name] = BrownieArtifact.deploy({"from": deployer})

    def add_sett(
        self,
        id,
        token,
        controller,
        namePrefixOverride=False,
        namePrefix="",
        symbolPrefix="",
    ):
        deployer = self.deployer
        proxyAdmin = self.devProxyAdmin
        governance = deployer
        keeper = deployer

        print(
            "add_sett",
            token,
            controller,
            governance,
            keeper,
            namePrefixOverride,
            namePrefix,
            symbolPrefix,
        )

        sett = deploy_proxy(
            "Sett",
            Sett.abi,
            self.logic.Sett.address,
            proxyAdmin.address,
            self.logic.Sett.initialize.encode_input(
                token,
                controller,
                governance,
                keeper,
                namePrefixOverride,
                namePrefix,
                symbolPrefix,
            ),
            deployer,
        )
        self.sett_system.vaults[id] = sett
        self.track_contract_upgradeable(sett)
        return sett

    def add_strategy(self, id, strategyName, controller, params):
        # TODO: Replace with prod permissions config
        deployer = self.deployer

        strategy = deploy_strategy(self, strategyName, controller, params, deployer)

        self.sett_system.strategies[id] = strategy
        self.track_contract_upgradeable(strategy)
        return strategy

    def add_geyser(self, distToken, id):
        deployer = self.deployer
        geyser = deploy_geyser(self, distToken)
        self.geysers[id] = geyser
        self.track_contract_upgradeable(geyser)
        return geyser

    def deploy_sett_staking_rewards(self, id, stakingToken, distToken):
        deployer = self.deployer

        print(deployer, distToken, stakingToken)

        rewards = deploy_proxy(
            "StakingRewards",
            StakingRewards.abi,
            self.logic.StakingRewards.address,
            self.devProxyAdmin.address,
            self.logic.StakingRewards.initialize.encode_input(
                deployer, distToken, stakingToken
            ),
            deployer,
        )

        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(rewards)
        return rewards

    # ===== Function Call Macros =====

    def wire_up_sett(self, vault, strategy, controller):
        deployer = self.deployer

        want = strategy.want()
        vault_want = vault.token()

        assert vault_want == want

        controller.setVault(want, vault, {"from": deployer})

        controller.approveStrategy(
            want, strategy, {"from": deployer},
        )

        controller.setStrategy(
            want, strategy, {"from": deployer},
        )

    def distribute_staking_rewards(self, id, amount, notify=False):
        deployer = self.deployer
        rewards = self.getSettRewards(id)

        self.token.transfer(
            rewards, amount, {"from": deployer},
        )

        assert self.token.balanceOf(rewards) >= amount
        assert rewards.rewardsToken() == self.token
        if notify:
            rewards.notifyRewardAmount(amount, {"from": deployer})

    def signal_initial_geyser_rewards(self, id, params):
        deployer = self.deployer
        startTime = badger_config.geyserParams.badgerDistributionStart
        geyser = self.getGeyser(id)

        self.rewardsEscrow.approveRecipient(geyser, {"from": deployer})

        self.rewardsEscrow.signalTokenLock(
            self.token, params.amount, params.duration, startTime, {"from": deployer},
        )

    # ===== Strategy Macros =====
    def deploy_strategy_preconfigured(self, id):
        if id == "native.badger":
            self.deploy_strategy_native_badger()
        if id == "native.renCrv":
            self.deploy_strategy_native_rencrv()
        if id == "native.sbtcCrv":
            self.deploy_strategy_native_sbtccrv()
        if id == "native.tbtcCrv":
            self.deploy_strategy_native_tbtccrv()
        if id == "native.uniBadgerWbtc":
            self.deploy_strategy_native_uniBadgerWbtc()
        if id == "pickle.renCrv":
            self.deploy_strategy_pickle_rencrv()
        if id == "harvest.renCrv":
            self.deploy_strategy_harvest_rencrv()

    def deploy_strategy_native_badger(self):
        sett = self.getSett("native.badger")
        controller = self.getController("native")
        params = sett_config.native.badger.params
        params.want = self.token
        params.geyser = self.getSettRewards("native.badger")

        strategy = self.add_strategy(
            "native.badger", "StrategyBadgerRewards", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_rencrv(self):
        sett = self.getSett("native.renCrv")
        controller = self.getController("native")
        params = sett_config.native.renCrv.params

        strategy = self.add_strategy(
            "native.renCrv", "StrategyCurveGaugeRenBtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_sbtccrv(self):
        sett = self.getSett("native.sbtcCrv")
        controller = self.getController("native")
        params = sett_config.native.sbtcCrv.params

        strategy = self.add_strategy(
            "native.sbtcCrv", "StrategyCurveGaugeSbtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_tbtccrv(self):
        sett = self.getSett("native.tbtcCrv")
        controller = self.getController("native")
        params = sett_config.native.tbtcCrv.params

        strategy = self.add_strategy(
            "native.tbtcCrv", "StrategyCurveGaugeTbtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_uniBadgerWbtc(self):
        sett = self.getSett("native.uniBadgerWbtc")
        controller = self.getController("native")
        params = sett_config.native.uniBadgerWbtc.params
        params.want = self.pair
        params.geyser = self.getSettRewards("native.uniBadgerWbtc")

        strategy = self.add_strategy(
            "native.uniBadgerWbtc", "StrategyBadgerLpMetaFarm", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_pickle_rencrv(self):
        sett = self.getSett("pickle.renCrv")
        controller = self.getController("pickle")
        params = sett_config.pickle.renCrv.params

        strategy = self.add_strategy(
            "pickle.renCrv", "StrategyPickleMetaFarm", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_harvest_rencrv(self):
        sett = self.getSett("harvest.renCrv")
        controller = self.getController("harvest")
        params = sett_config.harvest.renCrv.params
        params.badgerTree = self.badgerTree

        strategy = self.add_strategy(
            "harvest.renCrv", "StrategyHarvestMetaFarm", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def signal_token_lock(self, id, params):
        geyser = self.getGeyser(id)
        print('signal_token_lock', id, params, geyser, self.globalStartTime)
        self.rewardsEscrow.signalTokenLock(
            geyser,
            self.token,
            params.amount,
            params.duration,
            self.globalStartTime,
            {"from": self.deployer},
        )

    # ===== Getters =====

    def getGeyser(self, id):
        return self.geysers[id]

    def getController(self, id):
        return self.sett_system.controllers[id]

    def getSett(self, id):
        return self.sett_system.vaults[id]

    def getSettRewards(self, id):
        return self.sett_system.rewards[id]

    def getStrategy(self, id):
        return self.sett_system.strategies[id]

    def getStrategyWant(self, id):
        return interface.IERC20(self.sett_system.strategies[id].want())
