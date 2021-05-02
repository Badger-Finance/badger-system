from brownie import interface


class AaveSystem:
    def __init__(self, registry):
        self.registry = registry
        self.lendingPool = interface.ILendingPool(registry.aave.lendingPoolV2)

    def deposit(self, asset, amount, params):
        self.lendingPool.deposit(
            asset, amount, params["from"], 0, {"from": params["from"]}
        )
