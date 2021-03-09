from re import error
from dotmap import DotMap
from enum import Enum
from helpers.registry.eth import eth_registry
from helpers.registry.bsc import bsc_registry
from helpers.registry.artifacts import artifacts

from helpers.network import Chains, network_manager
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
        self.registries[Chains.ETH] = DotMap(
            curve= eth_registry.curve_registry,
            uniswap= eth_registry.uniswap_registry,
            open_zeppelin= eth_registry.open_zeppelin_registry,
            aragon= eth_registry.aragon_registry,
            sushiswap= eth_registry.sushi_registry,
            sushi= eth_registry.sushi_registry,
            gnosis_safe= eth_registry.gnosis_safe_registry,
            onesplit= eth_registry.gnosis_safe_registry,
            pickle= eth_registry.pickle_registry,
            harvest= eth_registry.harvest_registry,
            tokens= eth_registry.token_registry,
            whales= eth_registry.whale_registry,
            multicall= eth_registry.multicall_registry,
        )
        self.registries["bsc"] = DotMap(
            pancake= bsc_registry.pancake,
            gnosis_safe= bsc_registry.gnosis_safe_registry,
            tokens= bsc_registry.token_registry,
            multicall= bsc_registry.multicall_registry,
        )

    def has_registry(self, chain: Chains):
        return chain in self.registries.keys()

    def get_registry(self, chain: Chains):
        return self.registries[chain]

    def get_active_chain_registry(self) -> DotMap:
        network_id = network_manager.get_active_network()
        print(network_id)
        if not self.has_registry(network_id):
            console.print("[red]Chain ID {} not found[/red]".format(network_id))
        return self.get_registry(network_id)

registries = ContractRegistries()
registry = registries.get_active_chain_registry()
artifacts = artifacts
