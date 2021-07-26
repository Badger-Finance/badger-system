import json
from brownie import (
    web3,
    SwapStrategyRouter,
    CurveSwapStrategy,
    Contract,
    MockSwapStrategy,
    MockSwapStrategyRouter,
)
from dotmap import DotMap

from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.proxy_utils import deploy_proxy
from helpers.registry import artifacts
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from config.badger_config import swap_config

from rich.console import Console

console = Console()


def print_to_file(swap, path):
    system = {
        "swap_system": {"strategies": {}, "logic": {}},
    }

    for key, value in swap.strategies.items():
        system["swap_system"]["strategies"][key] = value.address

    for key, value in swap.logic.items():
        system["swap_system"]["logic"][key] = value.address

    with open(path, "w") as f:
        f.write(json.dumps(system, indent=4, sort_keys=True))


def connect_swap(badger_deploy_file):
    swap_deploy = {}
    console.print(
        "[grey]Connecting to Existing Swap 🦡 System at {}...[/grey]".format(
            badger_deploy_file
        )
    )
    with open(badger_deploy_file) as f:
        badger_deploy = json.load(f)
    """
    Connect to existing swap deployment
    """

    swap_deploy = badger_deploy["swap_system"]

    abi = artifacts.open_zeppelin["ProxyAdmin"]["abi"]
    swap = SwapSystem(
        badger_deploy["deployer"],
        Contract.from_abi(
            "ProxyAdmin",
            web3.toChecksumAddress(badger_deploy["devProxyAdmin"]),
            abi,
        ),
        swap_config,
    )
    swap.connect_logic(swap_deploy["logic"])

    # arguments: (attr name, address)
    strategies = swap_deploy["strategies"]
    connectable = [
        (
            "curve",
            "CurveSwapStrategy",
            strategies["curve"],
        ),
    ]
    for args in connectable:
        swap.connect_strategy(*args)

    swap.connect_router(swap_deploy["router"])

    return swap


name_to_artifact = {
    "CurveSwapStrategy": CurveSwapStrategy,
    "SwapStrategyRouter": SwapStrategyRouter,
}


class SwapSystem:
    """
    The SWAP system consists of swap router/strategies for routing of swaps.
    Currently, curve is the only supported swap strategy.
    """

    def __init__(self, deployer, devProxyAdmin, config, publish_source=False):
        self.deployer = deployer
        self.devProxyAdmin = devProxyAdmin
        self.config = config
        self.publish_source = publish_source
        # Admin is a multisig
        self.admin = connect_gnosis_safe(config.adminMultiSig)

        # Router ref, lazily set.
        self.router = None
        self.strategies = DotMap()
        self.logic = DotMap()
        # Mocks for testing only.
        self.mocks = DotMap()

    def connect_router(self, address) -> None:
        self.router = SwapStrategyRouter.at(address)

    def connect_strategy(self, name, artifactName, address):
        Artifact = name_to_artifact[artifactName]
        self.strategies[name] = Artifact.at(address)

    def connect_logic(self, logic):
        for name, address in logic.items():
            Artifact = name_to_artifact[name]
            self.logic[name] = Artifact.at(address)

    # ===== Deployers =====

    def deploy_logic(self):
        deployer = self.deployer
        self.logic = DotMap(
            CurveSwapStrategy=CurveSwapStrategy.deploy(
                {"from": deployer},
                publish_source=self.publish_source,
            ),
            SwapStrategyRouter=SwapStrategyRouter.deploy(
                {"from": deployer},
                publish_source=self.publish_source,
            ),
        )

    def deploy_router(self):
        admin = self.admin
        devProxyAdmin = self.devProxyAdmin
        self.router = deploy_proxy(
            "SwapStrategyRouter",
            SwapStrategyRouter.abi,
            self.logic.SwapStrategyRouter.address,
            web3.toChecksumAddress(devProxyAdmin.address),
            self.logic.SwapStrategyRouter.initialize.encode_input(
                admin.address,
            ),
            self.deployer,
        )

    def deploy_curve_swap_strategy(self):
        config = self.config
        admin = self.admin
        devProxyAdmin = self.devProxyAdmin
        self.strategies.curve = deploy_proxy(
            "CurveSwapStrategy",
            CurveSwapStrategy.abi,
            self.logic.CurveSwapStrategy.address,
            web3.toChecksumAddress(devProxyAdmin.address),
            self.logic.CurveSwapStrategy.initialize.encode_input(
                admin.address,
                config.strategies.curve.registry,
            ),
            self.deployer,
        )

    # ===== Configuration =====

    def configure_router(self):
        admin = self.admin
        multi = GnosisSafe(admin)
        for strategy in self.strategies.values():
            multi.execute(
                MultisigTxMetadata(
                    description="Add Swap Strategy {}".format(strategy.address)
                ),
                {
                    "to": strategy.address,
                    "data": self.router.addSwapStrategy.encode_input(strategy.address),
                },
            )

    # Grant swapper role to all strategies.
    def configure_strategies_grant_swapper_role(self, swapper):
        admin = self.admin
        multi = GnosisSafe(admin)
        for strategy in self.strategies.values():
            multi.execute(
                MultisigTxMetadata(
                    description="Add Swapper Role to {}".format(swapper)
                ),
                {
                    "to": strategy,
                    "data": strategy.grantRole.encode_input(
                        strategy.SWAPPER_ROLE(), swapper
                    ),
                },
            )

    # ===== Testing =====

    def deploy_mocks(self, router_fail=False):
        deployer = self.deployer
        strategy = MockSwapStrategy.deploy({"from": deployer})
        router = MockSwapStrategyRouter.deploy(
            strategy,
            router_fail,
            {"from": deployer},
        )

        self.mocks.router = router
        self.mocks.strategy = strategy
