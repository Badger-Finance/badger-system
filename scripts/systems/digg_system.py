import json
import decouple

from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.proxy_utils import deploy_proxy
from brownie import *
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import (
    badger_config,
    digg_config,
)

from rich.console import Console

console = Console()

# Constant oracle always reports a value of 1.
CONSTANT_ORACLE_VALUE = 1


def print_to_file(digg, path):
    system = {
        "owner": digg.owner.address,
        "devProxyAdmin": digg.owner.devProxyAdmin,
        "daoProxyAdmin": digg.owner.daoProxyAdmin,
        "uFragments": digg.uFragments.address,
        "uFragmentsPolicy": digg.uFragmentsPolicy.address,
        "orchestrator": digg.orchestrator.address,
        "cpiMedianOracle": digg.cpiMedianOracle.address,
        "constantOracle": digg.constantOracle.address,
        "daoDiggTimelock": digg.daoDiggTimelock.address,
        "diggTeamVesting": digg.diggTeamVesting.address,
        "logic": {},
    }

    for key, value in digg.logic.items():
        system["logic"][key] = value.address


def connect_digg(digg_deploy_file):
    digg_deploy = {}
    console.print(
        "[grey]Connecting to Existing Digg 🦡 System at {}...[/grey]".format(
            digg_deploy_file
        )
    )
    with open(digg_deploy_file) as f:
        digg_deploy = json.load(f)
    """
    Connect to existing digg deployment
    """

    digg = DiggSystem(
        digg_config,
        digg_deploy["owner"],
        digg_deploy["devProxyAdmin"],
        digg_deploy["daoProxyAdmin"],
    )

    connectable = [
        ("daoDiggTimelock", SimpleTimelock, address,),
        ("diggTeamVesting", SmartVesting, address,),
        ("uFragments", UFragments, address,),
        ("uFragmentsPolicy", UFragmentsPolicy, address,),
        ("constantOracle", ConstantOracle, address, False),
        ("cpiMedianOracle", MedianOracle, address, False),
        # TODO: connect market median oracle.
        ("orchestrator", Orchestrator, address, False),  # static, upgradeable=False
    ]
    for args in connectable:
        digg.connect(*args)

    return digg


class DiggSystem:
    def __init__(self, config, owner, devProxyAdmin, daoProxyAdmin):
        self.config = config
        self.contracts_static = []
        self.contracts_upgradeable = {}
        # Token is set when digg token (UFragments) is deployed.
        self.token = None

        if rpc.is_active():
            print("RPC Active")
            self.owner = accounts.at(owner, force=True)
        else:
            print("RPC Inactive")
            owner_key = decouple.config("DIGG_OWNER_PRIVATE_KEY")
            self.owner = accounts.add(owner_key)

        # TODO: Supply existing proxy admin
        self.connect_proxy_admins(devProxyAdmin, daoProxyAdmin)
        self.logic = DotMap()
        self.geysers = DotMap()

        self.connect_multisig()

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, key, contract):
        self.contracts_upgradeable[key] = contract

    # ===== Contract Connectors =====
    def connect_proxy_admins(self, devProxyAdmin, daoProxyAdmin):
        abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]

        self.devProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(devProxyAdmin), abi,
        )
        self.daoProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(daoProxyAdmin), abi,
        )

    def connect_multisig(self):
        deployer = self.owner

        multisigParams = badger_config["devMultisigParams"]
        multisigParams.owners = [deployer.address]

        print("Deploy Dev Multisig")
        self.devMultisig = connect_gnosis_safe(badger_config.multisig.address)


    def connect_dao(self):
        deployer = self.owner
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

    # ===== Deployers =====

    def deploy_core_logic(self):
        deployer = self.owner
        self.logic = DotMap(
            UFragments=UFragments.deploy({"from": deployer}),
            UFragmentsPolicy=UFragmentsPolicy.deploy({"from": deployer}),
        )

    def deploy_orchestrator(self):
        deployer = self.owner
        self.orchestrator = Orchestrator.deploy(self.uFragmentsPolicy, {'from': deployer})
        self.track_contract_static(self.orchestrator)

    def deploy_digg_policy(self):
        deployer = self.owner
        self.uFragmentsPolicy = deploy_proxy(
            "UFragmentsPolicy",
            UFragmentsPolicy.abi,
            self.logic.UFragmentsPolicy.address,
            self.devProxyAdmin.address,
            self.logic.UFragmentsPolicy.initialize.encode_input(
                self.owner,
                self.uFragments,
                self.config.baseCpi,
            ),
            deployer,
        )
        self.track_contract_upgradeable("uFragmentsPolicy", self.uFragmentsPolicy)

    def deploy_digg_token(self):
        deployer = self.deployer
        self.uFragments = deploy_proxy(
            "UFragments",
            UFragments.abi,
            self.logic.UFragments.address,
            self.devProxyAdmin.address,
            self.logic.UFragments.initialize.encode_input(
                self.owner,
                self.config.rebaseStartTimeUnixSeconds,
            ),
            deployer,
        )
        self.track_contract_upgradeable("uFragments", self.uFragments)

        # Set the digg system token after deploying.
        self.token = self.uFragments

    def deploy_constant_oracle(self):
        deployer = self.owner
        self.constantOracle = ConstantOracle.deploy(
            self.cpiMedianOracle,
            CONSTANT_ORACLE_VALUE,
            {'from': deployer},
        )
        self.track_contract_static(self.constantOracle)

    def deploy_cpi_median_oracle(self):
        deployer = self.owner
        self.cpiMedianOracle = MedianOracle.deploy(
            self.config.cpiOracleParams.reportExpirationTimeSec,
            self.config.cpiOracleParams.reportDelaySec,
            self.config.cpiOracleParams.minimumProviders,
            {'from': deployer},
        )
        self.track_contract_static(self.cpiMedianOracle)

    # TODO: deploy market median oracle

    def deploy_dao_digg_timelock(self):
        deployer = self.owner
        self.daoDiggTimelock = deploy_proxy(
            "SimpleTimelock",
            SimpleTimelock.abi,
            self.logic.SimpleTimelock.address,
            self.devProxyAdmin.address,
            self.logic.SimpleTimelock.initialize.encode_input(
                self.token,
                self.dao.agent,
                self.config.globalStartTime
                + self.config.tokenLockParams.lockDuration,
            ),
            deployer,
        )
        self.track_contract_upgradeable("daoDiggTimelock", self.daoDiggTimelock)

    def deploy_digg_team_vesting(self):
        deployer = self.owner

        self.teamVesting = deploy_proxy(
            "SmartVesting",
            SmartVesting.abi,
            self.logic.SmartVesting.address,
            self.devProxyAdmin.address,
            self.logic.SmartVesting.initialize.encode_input(
                self.token,
                self.devMultisig,
                self.dao.agent,
                self.config.globalStartTime,
                self.config.teamVestingParams.cliffDuration,
                self.config.teamVestingParams.totalDuration,
            ),
            deployer,
        )
        self.track_contract_upgradeable("teamVesting", self.diggTeamVesting)

    # ===== Connectors =====

    def connect(self, attr, BrownieArtifact, address, upgradeable=True):
        contract = BrownieArtifact.at(address)
        setattr(self, attr, contract)

        if upgradeable:
            self.track_contract_upgradeable(attr, contract)
        else:
            self.track_contract_static(contract)
