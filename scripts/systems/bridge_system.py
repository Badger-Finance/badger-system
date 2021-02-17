import json
from brownie import (
    BadgerBridgeAdapter,
    MockGatewayRegistry,
    MockGateway,
    ERC20,
)
from dotmap import DotMap

from helpers.registry import whale_registry
from helpers.token_utils import distribute_from_whale
from helpers.proxy_utils import deploy_proxy
from config.badger_config import bridge_config

from rich.console import Console

console = Console()


def print_to_file(bridge, path):
    system = {
        "bridge_system": {
            "logic": {},
        },
    }

    for key, value in bridge.logic.items():
        system["bridge_system"]["logic"][key] = value.address

    with open(path, "w") as f:
        f.write(json.dumps(system, indent=4, sort_keys=True))


def connect_bridge(badger_deploy_file):
    bridge_deploy = {}
    console.print(
        "[grey]Connecting to Existing 🦡 Bridge System at {}...[/grey]".format(
            badger_deploy_file
        )
    )
    with open(badger_deploy_file) as f:
        badger_deploy = json.load(f)
    """
    Connect to existing bridge deployment
    """

    bridge_deploy = badger_deploy["bridge_system"]

    bridge = BridgeSystem(
        bridge_config,
        badger_deploy["deployer"],
    )
    bridge.connect_bridge(bridge_deploy.bridge)

    return bridge


name_to_artifact = {
    "BadgerBridgeAdapter": BadgerBridgeAdapter,
}


class BridgeSystem:
    '''
    The BRIDGE system consists of a renVM mint/burn bridge and some mocking utilities for testing.
    Bridge zap contracts will be added at a later date.
    '''
    def __init__(self, deployer, config):
        self.deployer = deployer
        self.config = config

        # Bridge ref, lazily set.
        self.bridge = None
        self.strategies = DotMap()
        self.logic = DotMap()
        # Mocks for testing only.
        self.mocks = DotMap()

    def connect_bridge(self, address) -> None:
        self.bridge = BadgerBridgeAdapter.at(address)

    def connect_logic(self, logic):
        for name, address in logic.items():
            Artifact = name_to_artifact[name]
            self.logic[name] = Artifact.at(address)

    # ===== Deployers =====

    def deploy_bridge(
        self,
        registry,
        router,
    ):
        self.bridge = deploy_proxy(
            "BadgerBridgeAdapter",
            BadgerBridgeAdapter.abi,
            self.logic.BadgerBridgeAdapter.address,
            self.devProxyAdmin.address,
            self.logic.BadgerBridgeAdapter.initialize.encode_input(
                self.config.governance,
                self.config.rewardsAddress,
                registry,
                router,
                self.config.wbtc,
                [
                    self.config.mintFeeBps,
                    self.config.burnFeeBps,
                    self.config.percentageFeeRewardsBps,
                    self.config.percentageFeeGovernanceBps,
                ]
            ),
            self.deployer,
        )

    # ===== Testing =====

    def deploy_mocks(self):
        deployer = self.deployer
        registry = MockGatewayRegistry.deploy({"from": deployer})
        for (tokenName, whaleConfig) in [("BTC", whale_registry.renBTC)]:
            token = ERC20.at(whaleConfig.token)
            gateway = MockGateway.deploy(token.address, {"from": deployer})
            # Distribute token from whale -> mock gateway.
            distribute_from_whale(whaleConfig, gateway)
            self.mocks[tokenName] = DotMap(
                token=token,
                gateway=gateway,
            )
            registry.addGateway(tokenName, gateway.address)
            registry.addToken(tokenName, token.address)
        self.mocks.registry = registry
