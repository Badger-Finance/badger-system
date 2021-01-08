from brownie import (
    accounts,
    interface,
    web3,
    chain,
)

from scripts.systems.uniswap_system import UniswapSystem
from helpers.registry import registry


class SushiswapSystem(UniswapSystem):
    def __init__(self):
        self.contract_registry = registry.sushiswap
        self.factory = interface.IUniswapV2Factory(
            web3.toChecksumAddress(self.contract_registry.factory)
        )
        self.router = interface.IUniswapRouterV2(
            web3.toChecksumAddress(self.contract_registry.router)
        )
        self.chef = interface.ISushiChef(self.contract_registry.sushiChef)
        self.bar = interface.IxSushi(self.contract_registry.xsushiToken)

    def add_chef_rewards(self, pool):
        chef = self.chef

        owner = accounts.at(self.chef.owner(), force=True)

        avgAllocPoint = chef.totalAllocPoint() / chef.poolLength()
        chef.add(avgAllocPoint, pool, True, {"from": owner})

        pid = chef.poolLength() - 1
        chain.mine()

        chef.updatePool(pid, {"from": owner})
        chain.mine()

        return pid

