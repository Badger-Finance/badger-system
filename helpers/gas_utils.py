from brownie.network.gas.strategies import GasNowStrategy, ExponentialScalingStrategy
from brownie.network import gas_price

exponential_scaling_config = {
    "initial_gas_price": "10 gwei",
    "max_gas_price": "1000 gwei",
}

class GasStrategies:
    def __init__(self):
        self.exponentialScaling = ExponentialScalingStrategy(
            initial_gas_price=exponential_scaling_config["initial_gas_price"],
            max_gas_price=exponential_scaling_config["max_gas_price"],
        )
        self.fast = GasNowStrategy("fast")
        self.rapid = GasNowStrategy("rapid")

    def set_default(self, strategy):
        gas_price(strategy)

gas_strategies = GasStrategies()
gas_strategies.set_default(gas_strategies.fast)
