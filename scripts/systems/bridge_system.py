import json
from brownie import (
    web3,
    BadgerBridgeAdapter,
    MockGatewayRegistry,
    MockGateway,
    ERC20,
)
from dotmap import DotMap

from scripts.systems.swap_system import SwapSystem
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
    bridge.connect_adapter(bridge_deploy.adapter)

    return bridge


name_to_artifact = {
    "BadgerBridgeAdapter": BadgerBridgeAdapter,
}


class BridgeSystem:
    '''
    The BRIDGE system consists of a renVM mint/burn bridge and some mocking utilities for testing.
    Bridge zap contracts will be added at a later date.
    '''
    def __init__(self, deployer, devProxyAdmin, config, publish_source=False):
        self.deployer = deployer
        self.devProxyAdmin = devProxyAdmin
        self.config = config
        self.publish_source = publish_source

        # Adapter ref, lazily set.
        self.adapter = None
        # Swap ref, lazily set.
        self.swap = None
        self.strategies = DotMap()
        self.logic = DotMap()
        # Mocks for testing only.
        self.mocks = DotMap()

    def connect_adapter(self, address) -> None:
        self.adapter = BadgerBridgeAdapter.at(address)

    def connect_logic(self, logic):
        for name, address in logic.items():
            Artifact = name_to_artifact[name]
            self.logic[name] = Artifact.at(address)

    def add_existing_swap(self, swap_system: SwapSystem):
        self.swap = swap_system

    # ===== Deployers =====

    def deploy_adapter(
        self,
        registry,
        router,
    ):
        config = self.config
        deployer = self.deployer
        devProxyAdmin = self.devProxyAdmin
        logic = self.logic
        self.adapter = deploy_proxy(
            "BadgerBridgeAdapter",
            BadgerBridgeAdapter.abi,
            logic.BadgerBridgeAdapter.address,
            web3.toChecksumAddress(devProxyAdmin.address),
            logic.BadgerBridgeAdapter.initialize.encode_input(
                config.governance,
                config.rewards,
                registry,
                router,
                config.wbtc,
                [
                    config.mintFeeBps,
                    config.burnFeeBps,
                    config.percentageFeeRewardsBps,
                    config.percentageFeeGovernanceBps,
                ]
            ),
            deployer,
        )

    def deploy_logic(self, name, BrownieArtifact, test=False):
        deployer = self.deployer
        if test:
            self.logic[name] = BrownieArtifact.deploy({"from": deployer})
            return

        self.logic[name] = BrownieArtifact.deploy(
            {"from": deployer}, publish_source=self.publish_source
        )

    # ===== Testing =====

    def deploy_mocks(self):
        deployer = self.deployer
        registry = MockGatewayRegistry.deploy({"from": deployer})
        for (tokenName, whaleConfig) in [("BTC", whale_registry.renbtc)]:
            token = ERC20.at(whaleConfig.token)
            gateway = MockGateway.deploy(token.address, {"from": deployer})
            # Distribute token from whale -> deployer -> mock gateway.
            distribute_from_whale(whaleConfig, deployer, percentage=1.0)
            token.transfer(gateway, token.balanceOf(deployer), {"from": deployer})
            self.mocks[tokenName] = DotMap(
                token=token,
                gateway=gateway,
            )
            registry.addGateway(tokenName, gateway.address)
            registry.addToken(tokenName, token.address)
        self.mocks.registry = registry
