from helpers.time_utils import days
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from brownie.network.gas.strategies import GasNowScalingStrategy
from helpers.sett.strategy_registry import strategy_name_to_artifact
import json
import decouple

from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from brownie import *
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import (
    badger_config,
    sett_config,
)
from scripts.systems.sett_system import (
    deploy_controller,
    deploy_strategy,
)
from helpers.sett.strategy_registry import name_to_artifact
from scripts.systems.constants import SettType

from rich.console import Console

console = Console()


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
        "globalStartBlock": badger.globalStartBlock,
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
        "rewardsEscrow": badger.rewardsEscrow.address,
    }

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
    system["sett_system"]["strategy_artifacts"] = {}
    system["sett_system"]["rewards"] = {}

    for key, value in badger.sett_system.controllers.items():
        system["sett_system"]["controllers"][key] = value.address

    for key, value in badger.sett_system.vaults.items():
        system["sett_system"]["vaults"][key] = value.address

    for key, value in badger.sett_system.strategies.items():
        system["sett_system"]["strategies"][key] = value.address
        system["sett_system"]["strategy_artifacts"][
            key
        ] = badger.getStrategyArtifactName(key)

    for key, value in badger.sett_system.rewards.items():
        system["sett_system"]["rewards"][key] = value.address

    with open(path, "w") as outfile:
        json.dump(system, outfile)


def connect_badger(
    badger_deploy_file, load_deployer=False, load_keeper=False, load_guardian=False
):
    badger_deploy = {}
    console.print(
        "[grey]Connecting to Existing Badger 🦡 System at {}...[/grey]".format(
            badger_deploy_file
        )
    )
    with open(badger_deploy_file) as f:
        badger_deploy = json.load(f)

    """
    Connect to existing badger deployment
    """

    badger = BadgerSystem(
        badger_config,
        badger_deploy["deployer"],
        badger_deploy["keeper"],
        badger_deploy["guardian"],
        deploy=False,
        load_deployer=load_deployer,
        load_keeper=load_keeper,
        load_guardian=load_guardian,
    )

    badger.globalStartBlock = badger_deploy["globalStartBlock"]

    badger.connect_proxy_admins(
        badger_deploy["devProxyAdmin"], badger_deploy["daoProxyAdmin"]
    )

    badger.connect_logic(badger_deploy["logic"])

    # badger.connect_dev_multisig(badger_deploy["devMultisig"])
    badger.connect_uni_badger_wbtc_lp(badger_deploy["uniBadgerWbtcLp"])

    # Connect Vesting / Rewards Infrastructure
    badger.connect_team_vesting(badger_deploy["teamVesting"])
    badger.connect_badger_hunt(badger_deploy["badgerHunt"])
    badger.connect_badger_tree(badger_deploy["badgerTree"])
    badger.connect_rewards_escrow(badger_deploy["rewardsEscrow"])
    badger.connect_honeypot_meme(badger_deploy["honeypotMeme"])
    badger.connect_community_pool(badger_deploy["communityPool"])
    badger.connect_dao_badger_timelock(badger_deploy["daoBadgerTimelock"])

    # Connect Sett
    badger.connect_sett_system(badger_deploy["sett_system"], badger_deploy["geysers"])

    return badger


default_gas_strategy = GasNowScalingStrategy()


class BadgerSystem:
    def __init__(
        self,
        config,
        deployer,
        keeper,
        guardian,
        deploy=True,
        load_deployer=False,
        load_keeper=False,
        load_guardian=False,
    ):
        self.config = config
        self.contracts_static = []
        self.contracts_upgradeable = {}
        self.gas_strategy = default_gas_strategy

        # Unlock accounts in test mode
        if rpc.is_active():
            print("RPC Active")
            self.deployer = accounts.at(deployer, force=True)
            self.keeper = accounts.at(keeper, force=True)
            self.guardian = accounts.at(guardian, force=True)
        else:
            print("RPC Inactive")
            if load_deployer:
                deployer_key = decouple.config("DEPLOYER_PRIVATE_KEY")
                self.deployer = accounts.add(deployer_key)
            if load_keeper:
                keeper_key = decouple.config("KEEPER_PRIVATE_KEY")
                self.keeper = accounts.add(keeper_key)
            if load_guardian:
                guardian_key = decouple.config("GUARDIAN_PRIVATE_KEY")
                self.guardian = accounts.add(guardian_key)
        if deploy:
            self.devProxyAdmin = deploy_proxy_admin(deployer)
            self.daoProxyAdmin = deploy_proxy_admin(deployer)
            self.proxyAdmin = self.devProxyAdmin
        else:
            abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]
            self.devProxyAdmin = Contract.from_abi(
                "ProxyAdmin",
                web3.toChecksumAddress("0x20dce41acca85e8222d6861aa6d23b6c941777bf"),
                abi,
            )
            self.daoProxyAdmin = Contract.from_abi(
                "ProxyAdmin",
                web3.toChecksumAddress("0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2"),
                abi,
            )
            self.proxyAdmin = self.devProxyAdmin

        self.strategy_artifacts = DotMap()
        self.logic = DotMap()
        self.sett_system = DotMap(
            controllers=DotMap(), vaults=DotMap(), strategies=DotMap(), rewards=DotMap()
        )
        self.geysers = DotMap()

        self.connect_dao()
        self.connect_multisig()
        self.connect_uniswap()

        self.globalStartTime = badger_config.globalStartTime
        self.globalStartBlock = badger_config.globalStartBlock

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, key, contract):
        self.contracts_upgradeable[key] = contract

    # ===== Contract Connectors =====
    def connect_proxy_admins(self, devProxyAdmin, daoProxyAdmin):
        abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]

        self.devProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(devProxyAdmin), abi
        )
        self.daoProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(daoProxyAdmin), abi
        )

        self.proxyAdmin = self.devProxyAdmin

    def connect_dao(self):
        self.dao = DotMap(
            token=Contract.from_abi(
                "MiniMeToken",
                badger_config.dao.token,
                registry.aragon.artifacts.MiniMeToken["abi"]
            ),
            kernel=Contract.from_abi(
                "Agent",
                badger_config.dao.kernel,
                registry.aragon.artifacts.Agent["abi"]
            ),
            agent=Contract.from_abi(
                "Agent",
                badger_config.dao.agent,
                registry.aragon.artifacts.Agent["abi"]
            ),
        )

        self.token = self.dao.token

    def connect_multisig(self):
        self.devMultisig = connect_gnosis_safe(badger_config.multisig.address)

    def connect_treasury_multisig(self):
        self.treasuryMultisig = connect_gnosis_safe(
            badger_config.treasury_multisig.address
        )

    def connect_uniswap(self):
        self.uniswap = UniswapSystem()

    # ===== Deployers =====

    def add_controller(self, id):
        deployer = self.deployer
        controller = deploy_controller(self, deployer)
        self.sett_system.controllers[id] = controller
        self.track_contract_upgradeable(id + ".controller", controller)
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
        self.logic["Controller"] = Controller.deploy({"from": deployer})
        self.logic["Sett"] = Sett.deploy({"from": deployer})
        self.logic["DiggSett"] = DiggSett.deploy({"from": deployer})
        self.logic["StakingRewards"] = StakingRewards.deploy({"from": deployer})
        self.logic["StakingRewardsSignalOnly"] = StakingRewardsSignalOnly.deploy(
            {"from": deployer}
        )

    def deploy_sett_strategy_logic(self):
        deployer = self.deployer
        for name, artifact in name_to_artifact:
            self.logic[name] = artifact.deploy({"from": deployer})

    def deploy_sett_strategy_logic_for(self, name):
        deployer = self.deployer
        artifact = strategy_name_to_artifact(name)
        self.logic[name] = artifact.deploy(
            {"from": deployer, "gas_price": self.gas_strategy}
        )

        # TODO: Initialize to remove that function

    def set_gas_strategy(self, gas_strategy):
        self.gas_strategy = gas_strategy

    def deploy_rewards_escrow(self):
        deployer = self.deployer
        print("deployer", deployer)
        self.rewardsEscrow = deploy_proxy(
            "RewardsEscrow",
            RewardsEscrow.abi,
            self.logic.RewardsEscrow.address,
            self.devProxyAdmin.address,
            self.logic.RewardsEscrow.initialize.encode_input(),
            deployer,
        )
        self.track_contract_upgradeable("rewardsEscrow", self.rewardsEscrow)

    def deploy_badger_tree(self):
        deployer = self.deployer
        print(
            self.logic.BadgerTree.address,
            self.devProxyAdmin.address,
            self.devMultisig,
            self.keeper,
            self.guardian,
        )
        self.badgerTree = deploy_proxy(
            "BadgerTree",
            BadgerTree.abi,
            self.logic.BadgerTree.address,
            self.devProxyAdmin.address,
            self.logic.BadgerTree.initialize.encode_input(
                self.deployer, self.keeper, self.guardian
            ),
            deployer,
        )
        self.track_contract_upgradeable("badgerTree", self.badgerTree)

    def deploy_badger_hunt(self):
        deployer = self.deployer
        self.badgerHunt = deploy_proxy(
            "BadgerHunt",
            BadgerHunt.abi,
            self.logic.BadgerHunt.address,
            self.devProxyAdmin.address,
            self.logic.BadgerHunt.initialize.encode_input(
                self.token,
                badger_config.huntParams.merkleRoot,
                badger_config.huntParams.epochDuration,
                badger_config.huntParams.claimReductionPerEpoch,
                badger_config.huntParams.startTime,
                badger_config.huntParams.gracePeriod,
                self.rewardsEscrow,
                self.deployer,
            ),
            deployer,
        )
        self.track_contract_upgradeable("badgerHunt", self.badgerHunt)

    def deploy_dao_badger_timelock(self):
        deployer = self.deployer
        print(
            self.token,
            self.dao.agent,
            badger_config.globalStartTime,
            badger_config.tokenLockParams.lockDuration,
            (
                badger_config.globalStartTime
                + badger_config.tokenLockParams.lockDuration
            ),
            chain.time(),
        )
        self.daoBadgerTimelock = deploy_proxy(
            "SimpleTimelock",
            SimpleTimelock.abi,
            self.logic.SimpleTimelock.address,
            self.devProxyAdmin.address,
            self.logic.SimpleTimelock.initialize.encode_input(
                self.token,
                self.dao.agent,
                badger_config.globalStartTime
                + badger_config.tokenLockParams.lockDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable("daoBadgerTimelock", self.daoBadgerTimelock)

    def deploy_dao_digg_timelock(self):
        deployer = self.deployer

    def deploy_team_vesting(self):
        deployer = self.deployer

        self.teamVesting = deploy_proxy(
            "SmartVesting",
            SmartVesting.abi,
            self.logic.SmartVesting.address,
            self.devProxyAdmin.address,
            self.logic.SmartVesting.initialize.encode_input(
                self.token,
                self.devMultisig,
                self.dao.agent,
                badger_config.globalStartTime,
                badger_config.teamVestingParams.cliffDuration,
                badger_config.teamVestingParams.totalDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable("teamVesting", self.teamVesting)

    def deploy_logic(self, name, BrownieArtifact):
        deployer = self.deployer
        self.logic[name] = BrownieArtifact.deploy({"from": deployer})

    def deploy_sett(
        self,
        id,
        token,
        controller,
        namePrefixOverride=False,
        namePrefix="",
        symbolPrefix="",
        governance=None,
        strategist=None,
        keeper=None,
        guardian=None,
        sett_type=SettType.DEFAULT,
    ):
        deployer = self.deployer
        proxyAdmin = self.devProxyAdmin

        if not governance:
            governance = deployer
        if not strategist:
            strategist = deployer
        if not keeper:
            keeper = deployer
        if not guardian:
            guardian = deployer
        if sett_type == SettType.DIGG:
            print("Deploying DIGG Sett")
            sett = deploy_proxy(
                "DiggSett",
                DiggSett.abi,
                self.logic.DiggSett.address,
                proxyAdmin.address,
                self.logic.DiggSett.initialize.encode_input(
                    token,
                    controller,
                    governance,
                    keeper,
                    guardian,
                    namePrefixOverride,
                    namePrefix,
                    symbolPrefix,
                ),
                deployer,
            )
        else:
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
                    guardian,
                    namePrefixOverride,
                    namePrefix,
                    symbolPrefix,
                ),
                deployer,
            )
        self.sett_system.vaults[id] = sett
        self.track_contract_upgradeable(id + ".sett", sett)
        return sett

    def deploy_strategy(
        self,
        id,
        strategyName,
        controller,
        params,
        governance=None,
        strategist=None,
        keeper=None,
        guardian=None,
    ):
        # TODO: Replace with prod permissions config
        deployer = self.deployer

        strategy = deploy_strategy(
            self,
            strategyName,
            controller,
            params,
            deployer,
            governance,
            strategist,
            keeper,
            guardian,
        )

        Artifact = strategy_name_to_artifact(strategyName)

        self.sett_system.strategies[id] = strategy
        self.set_strategy_artifact(id, strategyName, Artifact)
        self.track_contract_upgradeable(id + ".strategy", strategy)
        return strategy

    def deploy_geyser(self, stakingToken, id):
        print(stakingToken)
        deployer = self.deployer
        geyser = deploy_geyser(self, stakingToken)
        self.geysers[id] = geyser
        self.track_contract_upgradeable(id + ".geyser", geyser)
        return geyser

    def add_existing_digg(self, digg_system):
        self.digg_system = digg_system

    def deploy_digg_rewards_faucet(self, id, diggToken):
        deployer = self.deployer

        rewards = deploy_proxy(
            "StakingRewards",
            DiggRewardsFaucet.abi,
            self.logic.DiggRewardsFaucet.address,
            self.devProxyAdmin.address,
            self.logic.DiggRewardsFaucet.initialize.encode_input(
                deployer, diggToken
            ),
            deployer,
        )

        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(id + ".rewards", rewards)
        return rewards

    def deploy_set_staking_rewards_signal_only(self, id, admin, distToken):
        deployer = self.deployer

        rewards = deploy_proxy(
            "StakingRewardsSignalOnly",
            StakingRewardsSignalOnly.abi,
            self.logic.StakingRewardsSignalOnly.address,
            self.devProxyAdmin.address,
            self.logic.StakingRewardsSignalOnly.initialize.encode_input(
                admin, distToken
            ),
            deployer,
        )

        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(id + ".rewards", rewards)
        return rewards

    def deploy_sett_staking_rewards(self, id, stakingToken, distToken):
        deployer = self.deployer

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
        self.track_contract_upgradeable(id + ".rewards", rewards)
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

        rewardsToken = interface.IERC20(rewards.rewardsToken())

        assert rewardsToken.balanceOf(deployer) >= amount

        rewardsToken.transfer(
            rewards, amount, {"from": deployer},
        )

        ## uint256 startTimestamp, uint256 _rewardsDuration, uint256 reward
        assert rewardsToken.balanceOf(rewards) >= amount
        if notify:
            rewards.notifyRewardAmount(chain.time(), days(7), amount, {"from": deployer})

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

        strategy = self.deploy_strategy(
            "native.badger", "StrategyBadgerRewards", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_rencrv(self):
        sett = self.getSett("native.renCrv")
        controller = self.getController("native")
        params = sett_config.native.renCrv.params

        strategy = self.deploy_strategy(
            "native.renCrv", "StrategyCurveGaugeRenBtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_sbtccrv(self):
        sett = self.getSett("native.sbtcCrv")
        controller = self.getController("native")
        params = sett_config.native.sbtcCrv.params

        strategy = self.deploy_strategy(
            "native.sbtcCrv", "StrategyCurveGaugeSbtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_tbtccrv(self):
        sett = self.getSett("native.tbtcCrv")
        controller = self.getController("native")
        params = sett_config.native.tbtcCrv.params

        strategy = self.deploy_strategy(
            "native.tbtcCrv", "StrategyCurveGaugeTbtcCrv", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_native_uniBadgerWbtc(self):
        sett = self.getSett("native.uniBadgerWbtc")
        controller = self.getController("native")
        params = sett_config.native.uniBadgerWbtc.params
        params.want = self.pair
        params.geyser = self.getSettRewards("native.uniBadgerWbtc")

        strategy = self.deploy_strategy(
            "native.uniBadgerWbtc", "StrategyBadgerLpMetaFarm", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def deploy_strategy_harvest_rencrv(self):
        sett = self.getSett("harvest.renCrv")
        controller = self.getController("harvest")
        params = sett_config.harvest.renCrv.params
        params.badgerTree = self.badgerTree

        strategy = self.deploy_strategy(
            "harvest.renCrv", "StrategyHarvestMetaFarm", controller, params
        )

        self.wire_up_sett(sett, strategy, controller)

    def signal_token_lock(self, id, params):
        geyser = self.getGeyser(id)
        self.rewardsEscrow.signalTokenLock(
            geyser,
            self.token,
            params.amount,
            params.duration,
            self.globalStartTime,
            {"from": self.deployer},
        )

    def upgrade_sett(self, id, newLogic):
        sett = self.getSett(id)
        multi = GnosisSafe(self.devMultisig)
        id = multi.addTx(
            MultisigTxMetadata(
                description="Upgrade timelock"
            ),
            {
                "to": self.proxyAdmin.address,
                "data": self.proxyAdmin.upgrade.encode_input(
                    sett,
                    newLogic
                ),
            },
            )
        tx = multi.executeTx(id)

    # ===== Connectors =====
    def connect_sett_system(self, sett_system, geysers):
        # Connect Controllers
        for key, address in sett_system["controllers"].items():
            self.connect_controller(key, address)

        # Connect Setts
        for key, address in sett_system["vaults"].items():
            self.connect_sett(key, address)

        # Connect Strategies
        for key, address in sett_system["strategies"].items():
            artifactName = sett_system["strategy_artifacts"][key]
            self.connect_strategy(key, address, artifactName)

        # Connect Rewards
        for key, address in sett_system["rewards"].items():
            self.connect_sett_staking_rewards(key, address)

        # Connect Geysers
        for key, address in geysers.items():
            self.connect_geyser(key, address)

    def connect_strategy(self, id, address, strategyArtifactName):
        Artifact = strategy_name_to_artifact(strategyArtifactName)
        strategy = Artifact.at(address)
        self.sett_system.strategies[id] = strategy
        self.set_strategy_artifact(id, strategyArtifactName, Artifact)
        self.track_contract_upgradeable(id + ".strategy", strategy)

    def connect_sett(self, id, address):
        sett = Sett.at(address)
        self.sett_system.vaults[id] = sett
        self.track_contract_upgradeable(id + ".sett", sett)

    def connect_controller(self, id, address):
        controller = Controller.at(address)
        self.sett_system.controllers[id] = controller
        self.track_contract_upgradeable(id + ".controller", controller)

    def connect_geyser(self, id, address):
        geyser = BadgerGeyser.at(address)
        self.geysers[id] = geyser
        self.track_contract_upgradeable(id + ".geyser", geyser)

    def connect_rewards_escrow(self, address):
        self.rewardsEscrow = RewardsEscrow.at(address)
        self.track_contract_upgradeable("rewardsEscrow", self.rewardsEscrow)

    def connect_badger_tree(self, address):
        self.badgerTree = BadgerTree.at(address)
        self.track_contract_upgradeable("badgerTree", self.badgerTree)

    def connect_badger_hunt(self, address):
        self.badgerHunt = BadgerHunt.at(address)
        self.track_contract_upgradeable("badgerHunt", self.badgerHunt)

    def connect_honeypot_meme(self, address):
        self.honeypotMeme = HoneypotMeme.at(address)
        self.track_contract_upgradeable("rewardsEscrow", self.rewardsEscrow)

    def connect_community_pool(self, address):
        self.communityPool = RewardsEscrow.at(address)
        self.track_contract_upgradeable("rewardsEscrow", self.rewardsEscrow)

    def connect_logic(self, logic):
        for name, address in logic.items():
            Artifact = strategy_name_to_artifact(name)
            self.logic[name] = Artifact.at(address)

    def connect_dao_badger_timelock(self, address):
        self.daoBadgerTimelock = SimpleTimelock.at(address)
        self.track_contract_upgradeable("daoBadgerTimelock", self.daoBadgerTimelock)

    def connect_dao_digg_timelock(self, address):
        # TODO: Implement with Digg
        return False

    def connect_team_vesting(self, address):
        self.teamVesting = SmartVesting.at(address)
        self.track_contract_upgradeable("teamVesting", self.teamVesting)

    def connect_sett_staking_rewards(self, id, address):
        pool = StakingRewards.at(address)
        self.sett_system.rewards[id] = pool
        self.track_contract_upgradeable(id + ".pool", pool)

    # def connect_guardian(self, address):
    #     self.guardian = accounts.at(address)

    # def connect_keeper(self, address):
    #     self.keeper = accounts.at(address)

    # def connect_deployer(self, address):
    #     self.deployer = accounts.at(address)

    def connect_uni_badger_wbtc_lp(self, address):
        self.pair = Contract.from_abi(
            "UniswapV2Pair", address, registry.uniswap.artifacts.UniswapV2Pair["abi"]
        )
        self.uniBadgerWbtcLp = self.pair

    def set_strategy_artifact(self, id, artifactName, artifact):
        self.strategy_artifacts[id] = {
            "artifact": artifact,
            "artifactName": artifactName,
        }

    # ===== Connect =====
    def get_keeper_account(self):
        if rpc.is_active():
            return accounts.at(self.keeper, force=True)
        else:
            priv = decouple.config("KEEPER_PRIVATE_KEY")
            return (
                accounts.add(priv) if priv else accounts.load(input("keeper account: "))
            )

    def get_guardian_account(self):
        if rpc.is_active():
            return accounts.at(self.guardian, force=True)
        else:
            priv = decouple.config("GUARDIAN_PRIVATE_KEY")
            return (
                accounts.add(priv)
                if priv
                else accounts.load(input("guardian account: "))
            )

    # ===== Getters =====

    def getGeyser(self, id):
        return self.geysers[id]

    def getController(self, id):
        return self.sett_system.controllers[id]

    def getControllerFor(self, id):
        controllerId = id.split(".", 1)[0]
        return self.sett_system.controllers[id]

    def getSett(self, id):
        if not id in self.sett_system.vaults.keys():
            console.print("[bold red]Sett not found:[/bold red] {}".format(id))
            raise NameError

        return self.sett_system.vaults[id]

    def getSettRewards(self, id):
        return self.sett_system.rewards[id]

    def getStrategy(self, id):
        if not id in self.sett_system.strategies.keys():
            console.print("[bold red]Strategy not found:[/bold red] {}".format(id))
            raise NameError

        return self.sett_system.strategies[id]

    def getStrategyWant(self, id):
        return interface.IERC20(self.sett_system.strategies[id].want())

    def getStrategyArtifact(self, id):
        return self.strategy_artifacts[id].artifact

    def getStrategyArtifactName(self, id):
        return self.strategy_artifacts[id]["artifactName"]
