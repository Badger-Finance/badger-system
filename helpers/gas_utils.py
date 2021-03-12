from brownie.network.gas.strategies import GasNowStrategy, ExponentialScalingStrategy
from brownie.network import gas_price
from brownie import Wei

exponential_scaling_config = {
    "initial_gas_price": "100 gwei",
    "max_gas_price": "1000 gwei",
}

class GasStrategies:
    def __init__(self):
        self.standard = GasNowStrategy("standard")
        self.fast = GasNowStrategy("fast")
        self.rapid = GasNowStrategy("rapid")

        print(self.fast.get_gas_price())

        self.exponentialScaling = ExponentialScalingStrategy(
            initial_gas_price=self.fast.get_gas_price(),
            max_gas_price=Wei(exponential_scaling_config["max_gas_price"]),
        )

    def set_default(self, strategy):
        gas_price(strategy)

gas_strategies = GasStrategies()
gas_strategies.set_default(gas_strategies.fast)
