from helpers.sett.strategy_registry import contract_name_to_artifact
import json
from brownie import *
from dotmap import DotMap

from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from scripts.systems.uniswap_system import UniswapSystem
from helpers.proxy_utils import deploy_proxy, deploy_proxy_uninitialized
from helpers.registry import registry, artifacts
from config.env_config import env_config
from config.badger_config import (
    badger_config,
    digg_config,
)

from rich.console import Console

console = Console()

# Constant oracle always reports a value of 1 w/ 18 decimal precision.
CONSTANT_ORACLE_VALUE = 1 * 10 ** 18


def print_to_file(digg, path):
    system = {
        "owner": digg.owner.address,
        "devProxyAdmin": digg.devProxyAdmin.address,
        "daoProxyAdmin": digg.daoProxyAdmin.address,
        "uFragments": digg.uFragments.address,
        "uFragmentsPolicy": digg.uFragmentsPolicy.address,
        "orchestrator": digg.orchestrator.address,
        "cpiMedianOracle": digg.cpiMedianOracle.address,
        "constantOracle": digg.constantOracle.address,
        # "daoDiggTimelock": digg.daoDiggTimelock.address,
        # "diggTeamVesting": digg.diggTeamVesting.address,
        "logic": {},
    }

    for key, value in digg.logic.items():
        system["logic"][key] = value.address


def connect_digg(badger_deploy_file):
    digg_deploy = {}
    console.print(
        "[grey]Connecting to Existing Digg 🦡 System at {}...[/grey]".format(
            badger_deploy_file
        )
    )
    with open(badger_deploy_file) as f:
        badger_deploy = json.load(f)
    """
    Connect to existing digg deployment
    """

    digg_deploy = badger_deploy["digg_system"]

    digg = DiggSystem(
        digg_config,
        badger_deploy["deployer"],
        badger_deploy["devProxyAdmin"],
        badger_deploy["daoProxyAdmin"],
        owner=badger_deploy["deployer"],
    )
    # arguments: (attr name, brownie artifact, address, upgradeable (default=True))
    connectable = [
        ("daoDiggTimelock", SimpleTimelock, digg_deploy["daoDiggTimelock"],),
        ("diggTeamVesting", SmartVesting, digg_deploy["diggTeamVesting"],),
        ("diggDistributor", DiggDistributor, digg_deploy["diggDistributor"],),
        # ("diggDistributor", DiggDistributor, digg_deploy["diggDistributor"],),
        ("uFragments", UFragments, digg_deploy["uFragments"],),
        ("uFragmentsPolicy", UFragmentsPolicy, digg_deploy["uFragmentsPolicy"],),
        ("constantOracle", ConstantOracle, digg_deploy["constantOracle"], False),
        ("cpiMedianOracle", MedianOracle, digg_deploy["cpiMedianOracle"], False),
        ("marketMedianOracle", MedianOracle, digg_deploy["marketMedianOracle"], False),
        ("orchestrator", Orchestrator, digg_deploy["orchestrator"], False),
    ]
    for args in connectable:
        if env_config.debug:
            print(args)
        digg.connect(*args)

    # token is a ref to uFragments
    digg.token = digg.uFragments

    digg.connect_logic(badger_deploy["logic"])
    digg.connect_centralized_oracle(digg_deploy["centralizedOracle"])

    # TODO: read these from config, hard configured for now. (Not set on init because token is lazily populated)
    # uniswap_pairs = [("digg_wbtc", digg.token.address, registry.tokens.wbtc)]
    # for args in uniswap_pairs:
    #     digg.connect_uniswap_pair(*args)

    return digg


class DiggSystem:
    def __init__(self, config, deployer, devProxyAdmin, daoProxyAdmin, owner=None):
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

        self.logic = DotMap()
        # Store uniswap trading pairs addresses.
        # Expected key syntax is `tokenA_tokenB`.
        self.uniswap_trading_pair_addrs = DotMap()

        if rpc.is_active():
            print("RPC Active")
            self.owner = accounts.at(owner, force=True)
        else:
            print("RPC Inactive")
            # owner_key = decouple.config("DIGG_OWNER_PRIVATE_KEY")
            # self.owner = accounts.add(owner_key)

        if deployer == None:
            console.print("[yellow]No deployer specified, using Owner[/yellow]")
            self.deployer = self.owner
        else:
            self.deployer = deployer
        if env_config.debug:
            print("deployer / owner", deployer, owner, self.deployer, self.owner)
        #        self.owner=""
        #        self.deployer=self.owner

        self.connect_proxy_admins(devProxyAdmin, daoProxyAdmin)
        self.connect_dao()
        self.connect_multisig()

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, key, contract):
        self.contracts_upgradeable[key] = contract

    def track_contract_ownable(self, contract):
        self.contracts_ownable.append(contract)

    # ===== Contract Connectors =====
    def connect_proxy_admins(self, devProxyAdmin, daoProxyAdmin):
        abi = artifacts.open_zeppelin["ProxyAdmin"]["abi"]

        self.devProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(devProxyAdmin), abi,
        )
        self.daoProxyAdmin = Contract.from_abi(
            "ProxyAdmin", web3.toChecksumAddress(daoProxyAdmin), abi,
        )

    def connect_centralized_oracle(self, address):
        self.centralizedOracle = connect_gnosis_safe(address)

    def connect_dao(self):
        deployer = self.deployer
        self.dao = DotMap(
            agent=Contract.from_abi(
                "Agent",
                badger_config.dao.agent,
                artifacts.aragon.Agent["abi"],
                deployer,
            ),
        )

    def connect_multisig(self):
        deployer = self.deployer

        if env_config.debug:
            print("Deploy Dev Multisig")
        self.devMultisig = connect_gnosis_safe(badger_config.multisig.address)

    def connect_uniswap_system(self):
        self.uniswap_system = UniswapSystem()

    def connect_uniswap_pair(self, pair_name, tokenA_addr, tokenB_addr):
        self.uniswap_trading_pair_addrs[pair_name] = self.uniswap_system.getPair(
            tokenA_addr, tokenB_addr
        )

    def connect(self, attr, BrownieArtifact, address, upgradeable=True):
        contract = BrownieArtifact.at(address)
        setattr(self, attr, contract)

        if upgradeable:
            self.track_contract_upgradeable(attr, contract)
        else:
            self.track_contract_static(contract)

    def connect_logic(self, logic):
        for name, address in logic.items():
            if env_config.debug:
                print("ConnectLogic:", name, address)
            Artifact = contract_name_to_artifact(name)
            self.logic[name] = Artifact.at(address)

    # ===== Deployers =====

    def deploy_core_logic(self):
        deployer = self.deployer
        self.logic = DotMap(
            # UFragments=UFragments.deploy({"from": deployer}),
            UFragments=UFragments.at("0xfabec03b04279c6e73f27aaf25866acc844448ae"),
            UFragmentsPolicy=UFragmentsPolicy.at(
                "0x4750caa4999404cb26ff6db2d0abc09b000122e0"
            ),
            # Timelock & Vesting: Use logic from existing badger deploy
            SimpleTimelock=SimpleTimelock.at(
                "0x4e3f56bb996ed91ba8d97ea773d3f818730d1a6f"
            ),
            SmartVesting=SmartVesting.at("0x07c0E4f4C977a29c46Fb26597ea8C9105ca50b42"),
            # DiggDistributor=DiggDistributor.deploy({"from": deployer}, publish_source=True),
        )

    def deploy_orchestrator(self):
        deployer = self.deployer
        self.orchestrator = Orchestrator.deploy(
            self.uFragmentsPolicy, {"from": deployer}
        )
        self.track_contract_static(self.orchestrator)
        self.track_contract_ownable(self.orchestrator)

    def deploy_digg_policy(self):
        deployer = self.deployer
        self.uFragmentsPolicy = deploy_proxy(
            "UFragmentsPolicy",
            UFragmentsPolicy.abi,
            self.logic.UFragmentsPolicy.address,
            self.devProxyAdmin.address,
            self.logic.UFragmentsPolicy.initialize.encode_input(
                self.owner, self.uFragments, self.config.baseCpi,
            ),
            deployer,
        )
        config = self.config

        # TODO: F/u on why these values are not being set.
        self.uFragmentsPolicy.setDeviationThreshold(
            config.deviationThreshold, {"from": deployer}
        )
        self.uFragmentsPolicy.setRebaseLag(config.rebaseLag, {"from": deployer})
        self.uFragmentsPolicy.setRebaseTimingParameters(
            config.minRebaseTimeIntervalSec,
            config.rebaseWindowOffsetSec,
            config.rebaseWindowLengthSec,
            {"from": deployer},
        )

        self.track_contract_upgradeable("uFragmentsPolicy", self.uFragmentsPolicy)
        self.track_contract_ownable(self.uFragmentsPolicy)

    def deploy_digg_token(self):
        deployer = self.owner
        self.uFragments = deploy_proxy(
            "UFragments",
            UFragments.abi,
            self.logic.UFragments.address,
            self.devProxyAdmin.address,
            self.logic.UFragments.initialize.encode_input(self.owner,),
            deployer,
        )
        self.track_contract_upgradeable("uFragments", self.uFragments)
        self.track_contract_ownable(self.uFragments)

        # Set the digg system token after deploying.
        # TODO: Move this to a better place.
        self.token = self.uFragments

    def deploy_constant_oracle(self):
        deployer = self.deployer
        self.constantOracle = ConstantOracle.deploy(
            self.cpiMedianOracle, {"from": deployer},
        )
        # self.constantOracle = ConstantOracle.deploy(
        #     self.cpiMedianOracle, {"from": deployer}, publish_source=True,
        # )
        self.track_contract_static(self.constantOracle)

    def deploy_cpi_median_oracle(self):
        deployer = self.deployer
        print("deploy_cpi_median_oracle", deployer)
        self.cpiMedianOracle = MedianOracle.deploy(
            self.config.cpiOracleParams.reportExpirationTimeSec,
            self.config.cpiOracleParams.reportDelaySec,
            self.config.cpiOracleParams.minimumProviders,
            {"from": deployer},
        )
        self.track_contract_static(self.cpiMedianOracle)
        self.track_contract_ownable(self.cpiMedianOracle)

    def deploy_market_median_oracle(self):
        deployer = self.deployer
        self.marketMedianOracle = MedianOracle.deploy(
            self.config.marketOracleParams.reportExpirationTimeSec,
            self.config.marketOracleParams.reportDelaySec,
            self.config.marketOracleParams.minimumProviders,
            {"from": deployer},
        )
        self.track_contract_static(self.marketMedianOracle)
        self.track_contract_ownable(self.marketMedianOracle)

    def deploy_dao_digg_timelock(self):
        deployer = self.deployer
        print(
            self.token,
            self.dao.agent,
            self.config.startTime + self.config.tokenLockParams.lockDuration,
            chain.time(),
        )
        self.daoDiggTimelock = deploy_proxy(
            "SimpleTimelock",
            SimpleTimelock.abi,
            self.logic.SimpleTimelock.address,
            self.devProxyAdmin.address,
            self.logic.SimpleTimelock.initialize.encode_input(
                self.token,
                self.dao.agent,
                self.config.startTime + self.config.tokenLockParams.lockDuration,
            ),
            deployer,
        )
        self.track_contract_upgradeable("daoDiggTimelock", self.daoDiggTimelock)

    def deploy_digg_team_vesting(self):
        deployer = self.deployer

        print(
            self.token,
            self.devMultisig,
            self.dao.agent,
            self.config.startTime,
            self.config.teamVestingParams.cliffDuration,
            self.config.teamVestingParams.totalDuration,
            chain.time(),
        )

        self.diggTeamVesting = deploy_proxy(
            "SmartVesting",
            SmartVesting.abi,
            self.logic.SmartVesting.address,
            self.devProxyAdmin.address,
            self.logic.SmartVesting.initialize.encode_input(
                self.token,
                self.devMultisig,
                self.dao.agent,
                self.config.startTime,
                self.config.teamVestingParams.cliffDuration,
                self.config.teamVestingParams.totalDuration,
            ),
            deployer,
        )
        self.track_contract_upgradeable("teamVesting", self.diggTeamVesting)

    def deploy_airdrop_distributor(self, root, rewardsEscrow, reclaimAllowedTimestamp):
        deployer = self.deployer

        self.diggDistributor = deploy_proxy(
            "DiggDistributor",
            DiggDistributor.abi,
            self.logic.DiggDistributor.address,
            self.devProxyAdmin.address,
            self.logic.DiggDistributor.initialize.encode_input(
                self.token, root, rewardsEscrow, reclaimAllowedTimestamp
            ),
            deployer,
        )

        self.track_contract_upgradeable("diggDistributor", self.diggDistributor)

    def deploy_airdrop_distributor_no_initialize(self):
        deployer = self.deployer

        self.diggDistributor = deploy_proxy_uninitialized(
            "DiggDistributor",
            DiggDistributor.abi,
            self.logic.DiggDistributor.address,
            self.devProxyAdmin.address,
            deployer,
        )

        self.track_contract_upgradeable("diggDistributor", self.diggDistributor)

    def deploy_uniswap_pairs(self, test=False):
        # TODO: read these from config, hard configured for now. (Not set on init because token is lazily populated)
        pairs = [("digg_wbtc", self.token.address, registry.tokens.wbtc)]
        for (pair_name, tokenA_addr, tokenB_addr) in pairs:
            self._deploy_uniswap_pair_idempotent(
                pair_name, tokenA_addr, tokenB_addr, test=test
            )

    def _deploy_uniswap_pair_idempotent(
        self, pair_name, tokenA_addr, tokenB_addr, test=False
    ):
        deployer = self.deployer

        # Deploy digg/wBTC pair if not already deployed.
        if not self.uniswap_system.hasPair(tokenA_addr, tokenB_addr):
            self.uniswap_system.createPair(tokenA_addr, tokenB_addr, deployer)
        self.uniswap_trading_pair_addrs[pair_name] = self.uniswap_system.getPair(
            tokenA_addr, tokenB_addr
        )

        # In test mode, add liquidity to uniswap.
        if test:
            self.uniswap_system.addMaxLiquidity(tokenA_addr, tokenB_addr, deployer)

    # ===== Administrative functions =====

    # Used on DEPLOY ONLY,  ownership of ownable contracts to a new owner.
    def transfer_ownership(self, owner):
        prevOwner = self.owner
        self.owner = owner
        for contract in self.contracts_ownable:
            contract.transferOwnership(owner, {"from": prevOwner})

    # ===== Deploy for TESTING ONLY =====

    # requires the market median oracle to be deployed as this feeds it data
    def deploy_dynamic_oracle(self):
        deployer = self.deployer
        self.dynamicOracle = DynamicOracle.deploy(
            self.marketMedianOracle, {"from": deployer},
        )
        self.track_contract_static(self.dynamicOracle)
