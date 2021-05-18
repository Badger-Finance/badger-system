from brownie import (
    interface,
    web3,
)

from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry


class PancakeswapSystem(SushiswapSystem):
    def __init__(self):
        self.contract_registry = registry.pancake
        self.factory = interface.IUniswapV2Factory(
            web3.toChecksumAddress(self.contract_registry.factoryV2)
        )
        self.router = interface.IUniswapRouterV2(
            web3.toChecksumAddress(self.contract_registry.routerV2)
        )
        self.chef = interface.ISushiChef(self.contract_registry.masterChef)
