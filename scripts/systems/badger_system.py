from helpers.rewards.LoggerUnlockSchedule import LoggerUnlockSchedule
from helpers.utils import digg_shares_to_initial_fragments, shares_to_fragments, val
from helpers.rewards.UnlockSchedule import UnlockSchedule
import json
import os
from eth_abi import encode_abi
from tabulate import tabulate
from web3 import Web3
from enum import Enum

from brownie import *
from brownie.network.gas.strategies import GasNowScalingStrategy
from config.badger_config import badger_config, sett_config
from dotmap import DotMap
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata, multisig_success
from helpers.network import network_manager
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from helpers.registry import artifacts, registry
from helpers.sett.strategy_registry import name_to_artifact, contract_name_to_artifact
from helpers.time_utils import days, to_days, to_utc_date
from rich.console import Console
from scripts.systems.claw_system import ClawSystem
from scripts.systems.constants import SettType, TIMELOCK_DIR
from scripts.systems.digg_system import DiggSystem, connect_digg
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from scripts.systems.sett_system import deploy_controller, deploy_strategy
from scripts.systems.swap_system import SwapSystem
from scripts.systems.uniswap_system import UniswapSystem

console = Console()


class LoadMethod(Enum):
    SK = 0
    KEYSTORE = 1


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

    if badger.digg:
        digg = badger.digg
        digg_system = {
            "owner": digg.owner.address,
            "devProxyAdmin": digg.devProxyAdmin.address,
            "daoProxyAdmin": digg.daoProxyAdmin.address,
            "uFragments": digg.uFragments.address,
            "uFragmentsPolicy": digg.uFragmentsPolicy.address,
            "orchestrator": digg.orchestrator.address,
            "cpiMedianOracle": digg.cpiMedianOracle.address,
            "constantOracle": digg.constantOracle.address,
            "diggDistributor": digg.diggDistributor.address,
            "daoDiggTimelock": digg.daoDiggTimelock.address,
            "diggTeamVesting": digg.diggTeamVesting.address,
            "logic": {},
        }

        for key, value in digg.logic.items():
            digg_system["logic"][key] = value.address

        system["digg_system"] = digg_system

    with open(path, "w") as f:
        f.write(json.dumps(system, indent=4, sort_keys=True))


def connect_badger(
    badger_deploy_file=False,
    load_deployer=False,
    load_keeper=False,
    load_guardian=False,
    load_method=LoadMethod.KEYSTORE,
):
    """
    Connect to an existing badger deploy from file
    Required Fields:
    devMultisig
    opsMultisig
    deployer
    keeper
    guardian

    """
    # TODO: fix this for networks
    # if not badger_deploy_file:
    badger_deploy_file = network_manager.get_active_network_badger_deploy()

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
        load_method=load_method,
    )

    # badger.globalStartBlock = badger_deploy["globalStartBlock"]

    dev_proxy_admin = None
    dao_proxy_admin = None
    ops_proxy_admin = None

    if "devProxyAdmin" in badger_deploy:
        dev_proxy_admin = badger_deploy["devProxyAdmin"]

    if "daoProxyAdmin" in badger_deploy:
        dao_proxy_admin = badger_deploy["daoProxyAdmin"]

    if "opsProxyAdmin" in badger_deploy:
        ops_proxy_admin = badger_deploy["opsProxyAdmin"]

    badger.connect_proxy_admins(dev_proxy_admin, dao_proxy_admin, ops_proxy_admin)

    if "testProxyAdmin" in badger_deploy:
        badger.connect_test_proxy_admin(
            "testProxyAdmin", badger_deploy["testProxyAdmin"]
        )

    badger.connect_multisig(badger_deploy["devMultisig"])
    badger.connect_ops_multisig(badger_deploy["opsMultisig"])

    if "dao" in badger_deploy:
        badger.connect_dao()

    if "treasuryMultisig" in badger_deploy:
        badger.connect_treasury_multisig(badger_deploy["treasuryMultisig"])

    badger.connect_logic(badger_deploy["logic"])

    # badger.connect_dev_multisig(badger_deploy["devMultisig"])

    # Connect Vesting / Rewards Infrastructure
    if "teamVesting" in badger_deploy:
        badger.connect_team_vesting(badger_deploy["teamVesting"])
    if "badgerHunt" in badger_deploy:
        badger.connect_badger_hunt(badger_deploy["badgerHunt"])
    if "badgerTree" in badger_deploy:
        badger.connect_badger_tree(badger_deploy["badgerTree"])
    if "rewardsEscrow" in badger_deploy:
        badger.connect_rewards_escrow(badger_deploy["rewardsEscrow"])
    if "honeypotMeme" in badger_deploy:
        badger.connect_honeypot_meme(badger_deploy["honeypotMeme"])
    if "communityPool" in badger_deploy:
        badger.connect_community_pool(badger_deploy["communityPool"])
    if "daoBadgerTimelock" in badger_deploy:
        badger.connect_dao_badger_timelock(badger_deploy["daoBadgerTimelock"])
    if "timelock" in badger_deploy:
        badger.connect_governance_timelock(badger_deploy["timelock"])
    if "badgerRewardsManager" in badger_deploy:
        badger.connect_rewards_manager(badger_deploy["badgerRewardsManager"])
    if "unlockScheduler" in badger_deploy:
        badger.connect_unlock_scheduler(badger_deploy["unlockScheduler"])
    if "rewardsLogger" in badger_deploy:
        badger.connect_rewards_logger(badger_deploy["rewardsLogger"])
    if "unifiedLogger" in badger_deploy:
        badger.connect_unified_logger(badger_deploy["unifiedLogger"])
    if "testGatedProxy" in badger_deploy:
        badger.connect_test_gated_proxy(badger_deploy["testGatedProxy"])
    if "opsGatedProxy" in badger_deploy:
        badger.connect_ops_gated_proxy(badger_deploy["opsGatedProxy"])

    # Connect Sett
    if "geysers" in badger_deploy:
        badger.connect_sett_system(
            badger_deploy["sett_system"], geysers=badger_deploy["geysers"]
        )
    else:
        badger.connect_sett_system(badger_deploy["sett_system"], geysers=None)

    # Connect DIGG
    if "digg_system" in badger_deploy:
        digg = connect_digg(badger_deploy_file)
        badger.add_existing_digg(digg)
    else:
        console.print("[yellow]No Digg found[/yellow]")

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
        load_method=LoadMethod.KEYSTORE,
    ):
        self.config = config
        self.contracts_static = []
        self.contracts_upgradeable = {}
        self.gas_strategy = default_gas_strategy
        # Digg system ref, lazily set.
        self.digg = None
        # Claw system ref, lazily set.
        self.claw = None
        # Swap system ref, lazily set.
        self.swap = None

        # Unlock accounts in test mode
        if rpc.is_active():
            print("RPC Active")
            self.deployer = accounts.at(deployer, force=True)
            self.keeper = accounts.at(keeper, force=True)
            self.guardian = accounts.at(guardian, force=True)
            self.publish_source = False
        else:
            print("RPC Inactive")
            import decouple

            print(load_deployer, load_keeper, load_guardian, load_method)

            if load_deployer and load_method == LoadMethod.SK:
                deployer_key = decouple.config("DEPLOYER_PRIVATE_KEY")
                self.deployer = accounts.add(deployer_key)
            if load_keeper and load_method == LoadMethod.SK:
                keeper_key = decouple.config("KEEPER_PRIVATE_KEY")
                self.keeper = accounts.add(keeper_key)
            if load_guardian and load_method == LoadMethod.SK:
                guardian_key = decouple.config("GUARDIAN_PRIVATE_KEY")
                self.guardian = accounts.add(guardian_key)
            if load_deployer and load_method == LoadMethod.KEYSTORE:
                self.deployer = accounts.load("badger-deployer")
            if load_keeper and load_method == LoadMethod.KEYSTORE:
                self.keeper = accounts.load("badger-keeper")
            if load_guardian and load_method == LoadMethod.KEYSTORE:
                self.guardian = accounts.load("badger-guardian")
            self.publish_source = False  # Publish sources for deployed logic on mainnet
        if deploy:
            self.devProxyAdmin = deploy_proxy_admin(deployer)
            self.daoProxyAdmin = deploy_proxy_admin(deployer)
            self.proxyAdmin = self.devProxyAdmin

        self.strategy_artifacts = DotMap()
        self.logic = DotMap()
        self.sett_system = DotMap(
            controllers=DotMap(), vaults=DotMap(), strategies=DotMap(), rewards=DotMap()
        )
        self.geysers = DotMap()

        self.globalStartTime = badger_config.globalStartTime
        self.globalStartBlock = badger_config.globalStartBlock

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, key, contract):
        self.contracts_upgradeable[key] = contract

    def connect_test_proxy_admin(self, name, address):
        abi = artifacts.open_zeppelin["ProxyAdmin"]["abi"]
        self.testProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(address), abi
        )
        return self.testProxyAdmin

    def connect_test_gated_proxy(self, address):
        self.testGatedProxy = GatedProxy.at(address)
        self.track_contract_upgradeable("testGatedProxy", self.testGatedProxy)

    def connect_ops_gated_proxy(self, address):
        self.opsGatedProxy = GatedProxy.at(address)
        self.track_contract_upgradeable("opsGatedProxy", self.opsGatedProxy)

    # ===== Contract Connectors =====
    def connect_proxy_admins(
        self, devProxyAdmin=None, daoProxyAdmin=None, opsProxyAdmin=None
    ):
        abi = artifacts.open_zeppelin["ProxyAdmin"]["abi"]

        if devProxyAdmin:
            self.devProxyAdmin = Contract.from_abi(
                "ProxyAdmin", web3.toChecksumAddress(devProxyAdmin), abi
            )
        else:
            self.devProxyAdmin = None
        if daoProxyAdmin:
            self.daoProxyAdmin = Contract.from_abi(
                "ProxyAdmin", web3.toChecksumAddress(daoProxyAdmin), abi
            )
        else:
            self.daoProxyAdmin = None

        if opsProxyAdmin:
            self.opsProxyAdmin = Contract.from_abi(
                "ProxyAdmin", web3.toChecksumAddress(opsProxyAdmin), abi
            )
        else:
            self.opsProxyAdmin = None

        self.testProxyAdmin = None

        self.proxyAdmin = self.devProxyAdmin

    def connect_dao(self):
        self.dao = DotMap(
            token=Contract.from_abi(
                "MiniMeToken",
                badger_config.dao.token,
                artifacts.aragon.MiniMeToken["abi"],
            ),
            kernel=Contract.from_abi(
                "Agent",
                badger_config.dao.kernel,
                artifacts.aragon.Agent["abi"],
            ),
            agent=Contract.from_abi(
                "Agent", badger_config.dao.agent, artifacts.aragon.Agent["abi"]
            ),
        )

        self.token = self.dao.token

    def connect_multisig(self, address):
        self.devMultisig = connect_gnosis_safe(address)

    def connect_treasury_multisig(self, address):
        self.treasuryMultisig = connect_gnosis_safe(address)

    def connect_ops_multisig(self, address):
        self.opsMultisig = connect_gnosis_safe(address)

    def connect_uniswap(self):
        self.uniswap = UniswapSystem()

    # ===== Deployers =====

    def add_controller(
        self,
        id,
        governance=None,
        strategist=None,
        keeper=None,
        rewards=None,
        proxyAdmin=None,
        deployer=None,
    ):

        if not deployer:
            deployer = self.deployer

        controller = deploy_controller(
            self, deployer, governance, strategist, keeper, rewards, proxyAdmin
        )
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

    def deploy_staking_rewards_logic(self):
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
        artifact = contract_name_to_artifact(name)
        self.logic[name] = artifact.deploy({"from": deployer})

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

    def deploy_logic(self, name, BrownieArtifact, test=False):
        deployer = self.deployer
        if test:
            self.logic[name] = BrownieArtifact.deploy({"from": deployer})
            return

        self.logic[name] = BrownieArtifact.deploy(
            {"from": deployer}, publish_source=self.publish_source
        )

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
        deployer=None,
        proxyAdmin=None,
    ):
        if not deployer:
            deployer = self.deployer
        if not proxyAdmin:
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

        Artifact = contract_name_to_artifact(strategyName)

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

    def add_existing_digg(self, digg_system: DiggSystem):
        self.digg = digg_system

    def deploy_digg_rewards_faucet(self, id, diggToken):
        deployer = self.deployer

        rewards = deploy_proxy(
            "DiggRewardsFaucet",
            DiggRewardsFaucet.abi,
            self.logic.DiggRewardsFaucet.address,
            self.devProxyAdmin.address,
            self.logic.DiggRewardsFaucet.initialize.encode_input(deployer, diggToken),
            deployer,
        )

        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(id + ".rewards", rewards)
        return rewards

    def deploy_sett_staking_rewards_signal_only(self, id, admin, distToken):
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

    def add_existing_claw(self, claw_system: ClawSystem):
        self.claw = claw_system

    def add_existing_swap(self, swap_system: SwapSystem):
        self.swap = swap_system

    # ===== Function Call Macros =====

    def wire_up_sett(self, vault, strategy, controller):
        deployer = self.deployer

        want = strategy.want()
        vault_want = vault.token()

        assert vault_want == want

        controller.setVault(want, vault, {"from": deployer})

        controller.approveStrategy(
            want,
            strategy,
            {"from": deployer},
        )

        controller.setStrategy(
            want,
            strategy,
            {"from": deployer},
        )

    def wire_up_sett_multisig(self, vault, strategy, controller):
        multi = GnosisSafe(self.devMultisig, testMode=True)

        want = strategy.want()
        vault_want = vault.token()

        assert vault_want == want

        id = multi.addTx(
            MultisigTxMetadata(
                description="Set Vault for {} on Controller".format(want)
            ),
            {
                "to": controller.address,
                "data": controller.setVault.encode_input(want, vault),
            },
        )
        multi.executeTx(id)

        id = multi.addTx(
            MultisigTxMetadata(
                description="Approve Strategy for {} on Controller".format(want)
            ),
            {
                "to": controller.address,
                "data": controller.approveStrategy.encode_input(want, strategy),
            },
        )
        multi.executeTx(id)

        id = multi.addTx(
            MultisigTxMetadata(
                description="Set Strategy for {} on Controller".format(want)
            ),
            {
                "to": controller.address,
                "data": controller.setStrategy.encode_input(want, strategy),
            },
        )
        multi.executeTx(id)

    def distribute_staking_rewards(self, id, amount, notify=False):
        deployer = self.deployer
        rewards = self.getSettRewards(id)

        rewardsToken = interface.IERC20(rewards.rewardsToken())

        assert rewardsToken.balanceOf(deployer) >= amount

        rewardsToken.transfer(
            rewards,
            amount,
            {"from": deployer},
        )

        ## uint256 startTimestamp, uint256 _rewardsDuration, uint256 reward
        assert rewardsToken.balanceOf(rewards) >= amount
        if notify:
            rewards.notifyRewardAmount(
                chain.time(), days(7), amount, {"from": deployer}
            )

    def signal_initial_geyser_rewards(self, id, params):
        deployer = self.deployer
        startTime = badger_config.geyserParams.badgerDistributionStart
        geyser = self.getGeyser(id)
        self.rewardsEscrow.approveRecipient(geyser, {"from": deployer})

        self.rewardsEscrow.signalTokenLock(
            self.token,
            params.amount,
            params.duration,
            startTime,
            {"from": deployer},
        )

    # ===== Strategy Macros =====
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

    # NB: Min gov timelock delay is 2 days.
    def queue_upgrade_sett(self, id, newLogic, delay=2 * days(2)) -> str:
        sett = self.getSett(id)
        return self.queue_upgrade(sett.address, newLogic.address)

    def queue_upgrade(self, proxyAddress, newLogicAddress, delay=2 * days(2)) -> str:
        target = self.devProxyAdmin.address
        signature = "upgrade(address,address)"
        data = encode_abi(["address", "address"], [proxyAddress, newLogicAddress])
        eta = web3.eth.getBlock("latest")["timestamp"] + delay
        return self.governance_queue_transaction(target, signature, data, eta)

    def timelock_run_direct(self, target, signature, data, eta, eth=0):
        multi = accounts.at(self.devMultisig.address, force=True)
        self.governanceTimelock.queueTransaction(
            target, eth, signature, data, eta, {"from": multi}
        )
        chain.sleep(days(5))
        self.governanceTimelock.executeTransaction(
            target, eth, signature, data, eta, {"from": multi}
        )

    def governance_queue_transaction(self, target, signature, data, eta, eth=0) -> str:
        multi = GnosisSafe(self.devMultisig)
        id = multi.addTx(
            MultisigTxMetadata(description="Queue timelock transaction"),
            {
                "to": self.governanceTimelock.address,
                "data": self.governanceTimelock.queueTransaction.encode_input(
                    target,
                    eth,
                    signature,
                    data,
                    eta,
                ),
            },
        )
        multi.executeTx(id)

        txHash = Web3.solidityKeccak(
            [
                "address",
                "uint256",
                "string",
                "bytes",
                "uint256",
            ],
            [
                target,
                eth,
                signature,
                data,
                eta,
            ],
        ).hex()

        txFilename = "{}.json".format(txHash)
        with open(os.path.join(TIMELOCK_DIR, txFilename), "w") as f:
            # Dump tx data to timelock pending tx dir.
            txData = {
                "target": target,
                "eth": eth,
                "signature": signature,
                "data": data.hex(),
                "eta": eta,
            }
            f.write(json.dumps(txData, indent=4, sort_keys=True))
        return txFilename

    def governance_execute_transaction(self, txFilename):
        multi = GnosisSafe(self.devMultisig)

        with open(os.path.join(TIMELOCK_DIR, txFilename), "r") as f:
            txData = json.load(f)
            id = multi.addTx(
                MultisigTxMetadata(description="Execute timelock transaction"),
                {
                    "to": self.governanceTimelock.address,
                    "data": self.governanceTimelock.executeTransaction.encode_input(
                        txData["target"],
                        txData["eth"],
                        txData["signature"],
                        txData["data"],
                        txData["eta"],
                    ),
                },
            )
            if multisig_success(multi.executeTx(id)):
                os.remove(os.path.join(TIMELOCK_DIR, txFilename))

    # ===== Connectors =====
    def connect_sett_system(self, sett_system, geysers=None):
        # Connect Controllers
        for key, address in sett_system["controllers"].items():
            self.connect_controller(key, address)

        # Connect Setts
        for key, address in sett_system["vaults"].items():
            artifactName = "Sett"
            if "vault_artifacts" in sett_system:
                artifactName = sett_system["vault_artifacts"][key]
            self.connect_sett(key, address, settArtifactName=artifactName)

        # Connect Strategies
        for key, address in sett_system["strategies"].items():
            artifactName = sett_system["strategy_artifacts"][key]
            self.connect_strategy(key, address, artifactName)

        # Connect Rewards
        for key, address in sett_system["rewards"].items():
            self.connect_rewards(key, address)

        # Connect Geysers
        if geysers:
            for key, address in geysers.items():
                self.connect_geyser(key, address)

    def connect_strategy(self, id, address, strategyArtifactName):
        Artifact = contract_name_to_artifact(strategyArtifactName)
        strategy = Artifact.at(address)
        self.sett_system.strategies[id] = strategy
        self.set_strategy_artifact(id, strategyArtifactName, Artifact)
        self.track_contract_upgradeable(id + ".strategy", strategy)

    def connect_sett(self, id, address, settArtifactName="Sett"):
        Artifact = contract_name_to_artifact(settArtifactName)
        sett = Artifact.at(address)
        print(f"connecting sett id {id}")
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
        self.badgerTree = BadgerTreeV2.at(address)
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
            Artifact = contract_name_to_artifact(name)
            self.logic[name] = Artifact.at(address)

    def connect_dao_badger_timelock(self, address):
        self.daoBadgerTimelock = SimpleTimelock.at(address)
        self.track_contract_upgradeable("daoBadgerTimelock", self.daoBadgerTimelock)

    def connect_governance_timelock(self, address):
        self.governanceTimelock = GovernanceTimelock.at(address)

    def connect_rewards_manager(self, address):
        self.badgerRewardsManager = BadgerRewardsManager.at(address)
        self.track_contract_upgradeable(
            "badgerRewardsManager", self.badgerRewardsManager
        )

    def connect_unlock_scheduler(self, address):
        self.unlockScheduler = UnlockScheduler.at(address)
        self.track_contract_upgradeable("unlockScheduler", self.unlockScheduler)

    def connect_rewards_logger(self, address):
        self.rewardsLogger = RewardsLogger.at(address)
        self.track_contract_upgradeable("rewardsLogger", self.rewardsLogger)

    def connect_unified_logger(self, address):
        self.unifiedLogger = UnifiedLogger.at(address)
        self.track_contract_upgradeable("unifiedLogger", self.unifiedLogger)

    def connect_dao_digg_timelock(self, address):
        # TODO: Implement with Digg
        return False

    def connect_team_vesting(self, address):
        self.teamVesting = SmartVesting.at(address)
        self.track_contract_upgradeable("teamVesting", self.teamVesting)

    # Routes rewards connection to correct underlying contract based on id.
    def connect_rewards(self, id, address):
        if id in [
            "native.digg",
            "native.uniDiggWbtc",
            "native.sushiDiggWbtc",
        ]:
            self.connect_digg_rewards_faucet(id, address)
            return
        self.connect_sett_staking_rewards(id, address)

    def connect_sett_staking_rewards(self, id, address):
        rewards = StakingRewards.at(address)
        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(id + ".rewards", rewards)

    # def connect_guardian(self, address):
    #     self.guardian = accounts.at(address)

    # def connect_keeper(self, address):
    #     self.keeper = accounts.at(address)

    # def connect_deployer(self, address):
    #     self.deployer = accounts.at(address)

    def connect_uni_badger_wbtc_lp(self, address):
        self.pair = Contract.from_abi(
            "UniswapV2Pair", address, artifacts.uniswap.UniswapV2Pair["abi"]
        )
        self.uniBadgerWbtcLp = self.pair

    def connect_digg_rewards_faucet(self, id, address):
        rewards = DiggRewardsFaucet.at(address)
        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(id + ".rewards", rewards)

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

    def setStrategy(self, id, strategy):
        self.sett_system.strategies[id] = strategy

    # ===== Getters =====

    def getGeyser(self, id):
        return self.geysers[id]

    def getController(self, id):
        return self.sett_system.controllers[id]

    def getControllerFor(self, id):
        controllerId = id.split(".", 1)[0]
        return self.sett_system.controllers[id]

    def getAllSettIds(self):
        ids = []
        for id in self.sett_system.vaults.keys():
            ids.append(id)
        return ids

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
    
    def getSettType(self, id):
        """
        Look at the artifact type of the sett and determine it's version. Currently hardcoded.
        """
        if id == "yearn.wbtc":
            return "v2"
        else:
            return "v1"

    def getStrategyArtifact(self, id):
        return self.strategy_artifacts[id].artifact

    def getStrategyArtifactName(self, id):
        return self.strategy_artifacts[id]["artifactName"]

    def getSeeder(self):
        """
        Return seeder account
        """
        if rpc.is_active():
            seeder = accounts.at(
                "0x3131B6964d96DE3Ad36C7Fe82e9bA9CcdBaf6baa", force=True
            )
        else:
            seeder = accounts.load("badger_proxy_deployer")
        return seeder

    def getLogic(self, logicName):
        if logicName in self.logic:
            return self.logic[logicName]
        else:
            raise Exception("Logic for {} not found".format(logicName))

    def getProxyAdmin(self, contract):
        potential_admins = self.getConnectedProxyAdmins()
        for name, admin in potential_admins.items():
            try:
                if admin.getProxyAdmin(contract) == admin:
                    return admin
            except:
                continue
        raise Exception(
            f"Contract not managed by any connected proxyAdmin from: {potential_admins}"
        )

    def getConnectedProxyAdmins(self):
        connected_admins = {}
        if self.devProxyAdmin:
            connected_admins["devProxyAdmin"] = self.devProxyAdmin
        if self.opsProxyAdmin:
            connected_admins["opsProxyAdmin"] = self.opsProxyAdmin
        if self.daoProxyAdmin:
            connected_admins["daoProxyAdmin"] = self.daoProxyAdmin
        if self.testProxyAdmin:
            connected_admins["testProxyAdmin"] = self.testProxyAdmin
        return connected_admins

    def get_latest_unlock_schedules(self, geyser):
        latest_schedules = {}
        tokens = geyser.getDistributionTokens()

        for token in tokens:
            schedules = geyser.getUnlockSchedulesFor(token)
            num_schedules = geyser.unlockScheduleCount(token)

            if num_schedules == 0:
                continue
            last_schedule = num_schedules - 1
            s = UnlockSchedule(token, schedules[last_schedule])

            latest_schedules[token] = s

        return latest_schedules

    def print_logger_unlock_schedules(self, beneficiary, name=None):
        logger = self.rewardsLogger

        schedules = logger.getAllUnlockSchedulesFor(beneficiary)

        if not name:
            name = ""

        console.print(f"[cyan]=== Latest Unlock Schedules {name}===[/cyan]")
        table = []

        if len(schedules) == 0:
            return
        for schedule in schedules:
            print(schedule)
            s = LoggerUnlockSchedule(schedule)

            digg_shares = s.token == self.digg.token

        if digg_shares:
            scaled = shares_to_fragments(s.amount)
        else:
            scaled = val(amount=s.amount, token=s.token)

        table.append(
            [
                name,
                s.beneficiary,
                s.token,
                scaled,
                to_days(s.duration),
                to_utc_date(s.start),
                to_utc_date(s.end),
                "{:.0f}".format(s.start),
                "{:.0f}".format(s.end),
            ]
        )

        print(
            tabulate(
                table,
                headers=[
                    "name",
                    "beneficiary",
                    "token",
                    "amount",
                    "duration",
                    "start",
                    "end",
                    "start",
                    "end",
                ],
            )
        )
        print("\n")

    def print_latest_unlock_schedules(self, geyser, name=None):
        if not name:
            name = ""

        console.print(f"[cyan]=== Latest Unlock Schedules {name}===[/cyan]")
        table = []
        tokens = geyser.getDistributionTokens()

        for token in tokens:
            schedules = geyser.getUnlockSchedulesFor(token)
            num_schedules = geyser.unlockScheduleCount(token)

            if num_schedules == 0:
                continue
            last_schedule = num_schedules - 1
            s = UnlockSchedule(token, schedules[last_schedule])

            digg_shares = token == self.digg.token

            if digg_shares:
                scaled = shares_to_fragments(s.amount)
            else:
                scaled = val(amount=s.amount, token=token)

            table.append(
                [
                    name,
                    token,
                    scaled,
                    to_days(s.duration),
                    to_utc_date(s.start),
                    to_utc_date(s.end),
                    "{:.0f}".format(s.start),
                    "{:.0f}".format(s.end),
                ]
            )

        print(
            tabulate(
                table,
                headers=[
                    "geyser",
                    "token",
                    "amount",
                    "duration",
                    "start",
                    "end",
                    "start",
                    "end",
                ],
            )
        )
        print("\n")
