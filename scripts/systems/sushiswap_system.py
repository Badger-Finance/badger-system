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
        # Make an average allocation of lp tokens.
        avgAllocPoint = chef.totalAllocPoint() / chef.poolLength()

        # Add pool if not exists and
        pid, exists = self._get_pool(pool)
        if exists:
            chef.set(avgAllocPoint, pool, True, {"from": owner})
        else:
            chef.add(avgAllocPoint, pool, True, {"from": owner})

        pid = chef.poolLength() - 1
        chain.mine()

        chef.updatePool(pid, {"from": owner})
        chain.mine()

        return pid

    def _get_pool(self, pool):
        chef = self.chef
        # Iterate over pools and look for pool first
        # NB: THIS IS EXPENSIVE AND SHOULD ONLY BE USED FOR TESTING.
        for pid in range(0, chef.poolLength()):
            (address, _, _, _) = chef.poolInfo(pid)
            if address == pool.address:
                return (pid, True)
        return (-1, False)
