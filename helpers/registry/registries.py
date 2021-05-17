from helpers.registry.ChainRegistry import ChainRegistry
from re import error
from dotmap import DotMap
from enum import Enum
from helpers.registry.eth_registry import eth_registry
from helpers.registry.bsc_registry import bsc_registry
from helpers.registry.artifacts import artifacts

from helpers.network import network_manager
from helpers.console_utils import console


class ContractSystems(Enum):
    ARAGON = ("aragon",)
    GNOSIS_SAFE = ("gnosis-safe",)
    OPEN_ZEPPELIN = ("open-zeppelin",)
    UNISWAP = ("uniswap",)
    SUSHISWAP = ("sushiswap",)
    MULTICALL = ("multicall",)
    PICKLE = ("pickle",)
    HARVEST = ("harvest",)
    CURVE = ("curve",)
    TOKENS = "tokens"


class ContractRegistries:
    """
    Contract registry for each chain
    """

    def __init__(self):
        self.registries = {}
        self.registries["eth"] = eth_registry
        self.registries["bsc"] = bsc_registry

    def has_registry(self, chain: str):
        return chain in self.registries.keys()

    def get_registry(self, chain: str):
        console.print("get_registry", chain)
        return self.registries[chain]

    def get_active_chain_registry(self) -> ChainRegistry:
        network_id = network_manager.get_active_network()
        if not self.has_registry(network_id):
            console.print("[red]Chain ID {} not found[/red]".format(network_id))
        return self.get_registry(network_id)


registries = ContractRegistries()
registry = registries.get_active_chain_registry()
artifacts = artifacts
