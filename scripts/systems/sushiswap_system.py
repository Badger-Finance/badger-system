from scripts.systems.uniswap_system import UniswapSystem
from helpers.utils import Eth
from brownie import *
from helpers.constants import AddressZero, MaxUint256
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

        totalAllocPoint = chef.totalAllocPoint()
        numPools = chef.totalAllocPoint()
        avgAllocPoint = totalAllocPoint / numPools

        owner = accounts.at(self.chef.owner(), force=True)

        chef.add(avgAllocPoint, pool, True, {f"from": owner})

        numPools = chef.totalAllocPoint()
        pid = numPools - 1
        print(pid, numPools)
        chain.mine()

        chef.updatePool(pid, {"from": owner})
        chain.mine()

        return pid

