import json
from brownie import SwapStrategyRouter, CurveSwapStrategy
from dotmap import DotMap

from helpers.proxy_utils import deploy_proxy
from config.badger_config import swap_config

from rich.console import Console

console = Console()


def print_to_file(swap, path):
    system = {
        "swap_system": {
            "strategies": {},
            "logic": {},
        },
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

    swap = SwapSystem(
        swap_config,
        badger_deploy["deployer"],
    )
    # arguments: (attr name, address)
    strategies = swap_deploy["strategies"]
    connectable = [
        ("CurveSwapStrategy", strategies["curve"],),
    ]
    for args in connectable:
        print(args)
        swap.connect_strategy(*args)

    swap.connect_router(swap_deploy.router)

    return swap


name_to_artifact = {
    "CurveSwapStrategy": CurveSwapStrategy,
    "SwapStrategyRouter": SwapStrategyRouter,
}


class SwapSystem:
    '''
    The SWAP system consists of swap router/strategies for routing of swaps.
    Currently, curve is the only supported swap strategy.
    '''
    def __init__(self, deployer, config):
        self.deployer = deployer
        self.config = config

        # Router ref, lazily set.
        self.router = None
        self.strategies = DotMap()
        self.logic = DotMap()

    def connect_router(self, address) -> None:
        self.router = SwapStrategyRouter.at(address)

    def connect_strategies(self, strategies):
        for name, address in strategies.items():
            Artifact = name_to_artifact[name]
            self.strategies[name] = Artifact.at(address)

    def connect_logic(self, logic):
        for name, address in logic.items():
            Artifact = name_to_artifact[name]
            self.logic[name] = Artifact.at(address)

    # ===== Deployers =====

    def deploy_logic(self):
        deployer = self.deployer
        self.logic = DotMap(
            CurveSwapStrategy=CurveSwapStrategy.deploy({"from": deployer}),
            SwapStrategyRouter=SwapStrategyRouter.deploy({"from": deployer}),
        )

    def deploy_router(self):
        config = self.config
        self.router = deploy_proxy(
            "SwapStrategyRouter",
            SwapStrategyRouter.abi,
            self.logic.SwapStrategyRouter.address,
            config.admin,
            self.logic.SwapStrategyRouter.initialize.encode_input(
                config.admin,
            ),
            self.deployer
        )

    def deploy_curve_swap_strategy(self):
        config = self.config
        self.strategies.curve = deploy_proxy(
            "CurveSwapStrategy",
            CurveSwapStrategy.abi,
            self.logic.CurveSwapStrategy.address,
            config.admin,
            self.logic.CurveSwapStrategy.initialize.encode_input(
                config.admin,
                config.strategies.curve.registry,
            ),
            self.deployer
        )

    def configure_router(self):
        config = self.config
        for strategy in self.strategies.values():
            self.router.addSwapStrategy(strategy.address, {"from": config.admin})
