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
    # arguments: (attr name, brownie artifact, address, upgradeable (default=True))
    connectable = [
        ("daoDiggTimelock", SimpleTimelock, digg_deploy["daoDiggTimelock"],),
        ("diggTeamVesting", SmartVesting, digg_deploy["diggTeamVesting"],),
        ("uFragments", UFragments, digg_deploy["uFragments"],),
        ("uFragmentsPolicy", UFragmentsPolicy, digg_deploy["uFragmentsPolicy"],),
        ("constantOracle", ConstantOracle, digg_deploy["constantOracle"], False),
        ("cpiMedianOracle", MedianOracle, digg_deploy["cpiMedianOracle"], False),
        ("marketMedianOracle", MedianOracle, digg_deploy["marketMedianOracle"], False),
        ("orchestrator", Orchestrator, address, False),
    ]
    for args in connectable:
        digg.connect(*args)

    return digg


class DiggSystem:
    def __init__(self, config, owner, devProxyAdmin, daoProxyAdmin):
        self.config = config
        self.contracts_static = []
        self.contracts_upgradeable = {}
        # These contracts adhere to the Ownable iface and belong to the
        # owner of the digg system (in prod it's the DAO). Note that this
        # is ONLY tracked on deploy as we will not modify ownership when
        # connecting to an existing system.
        self.contracts_ownable = []
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

    def track_contract_ownable(self, contract):
        self.contracts_ownable.append(contract)

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
        self.track_contract_ownable(self.orchestrator)

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
        self.track_contract_ownable(self.uFragmentsPolicy)

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
        self.track_contract_ownable(self.uFragments)

        # Set the digg system token after deploying.
        # TODO: Move this to a better place.
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
        self.track_contract_ownable(self.cpiMedianOracle)

    def deploy_market_median_oracle(self):
        deployer = self.owner
        self.marketMedianOracle = MedianOracle.deploy(
            self.config.marketOracleParams.reportExpirationTimeSec,
            self.config.marketOracleParams.reportDelaySec,
            self.config.marketOracleParams.minimumProviders,
            {'from': deployer},
        )
        self.track_contract_static(self.marketMedianOracle)
        self.track_contract_ownable(self.marketMedianOracle)

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

    # ===== Administrative functions =====

    # Used on DEPLOY ONLY, transfers ownership of ownable contracts to a new owner.
    def transfer_ownership(self, owner):
        prevOwner = self.owner
        self.owner = owner
        for contract in self.contracts_ownable:
            contract.transferOwnership(owner, {"from": prevOwner})

    # ===== Deploy for TESTING ONLY =====

    # requires the market median oracle to be deployed as this feeds it data
    def deploy_dynamic_oracle(self):
        deployer = self.owner
        self.dynamicOracle = DynamicOracle.deploy(
            self.marketMedianOracle,
            {'from': deployer},
        )
        self.track_contract_static(self.dynamicOracle)

    # ===== Connectors =====

    def connect(self, attr, BrownieArtifact, address, upgradeable=True):
        contract = BrownieArtifact.at(address)
        setattr(self, attr, contract)

        if upgradeable:
            self.track_contract_upgradeable(attr, contract)
        else:
            self.track_contract_static(contract)
