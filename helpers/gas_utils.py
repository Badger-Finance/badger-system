from brownie import network
from brownie.network.gas.strategies import (
    GasNowStrategy,
    ExponentialScalingStrategy,
    SimpleGasStrategy,
)
from brownie.network import gas_price
from brownie import Wei
from helpers.network import network_manager
from scripts.view.gas_intelligence import analyze_gas
from web3 import Web3

exponential_scaling_config = {
    "initial_gas_price": "100 gwei",
    "max_gas_price": "1000 gwei",
}

bsc_static_price = Wei("10 gwei")


class StaticGasStrategy(SimpleGasStrategy):
    def __init__(self, price) -> None:
        self.price = price
        super().__init__()

    def get_gas_price(self) -> int:
        return self.price


class GasStrategies:
    def __init__(self):
        self.standard = GasNowStrategy("standard")
        self.fast = GasNowStrategy("fast")
        self.rapid = GasNowStrategy("rapid")
        self.bsc_static = StaticGasStrategy(bsc_static_price)
        self.analyzed = analyze_gas({"timeframe": "minutes", "periods": 15})

        print(
            "gas prices - fast:",
            self.fast.get_gas_price(),
            "recent average:",
            self.analyzed.mode,
        )

        self.exponentialScaling = ExponentialScalingStrategy(
            initial_gas_price=self.standard.get_gas_price(),
            max_gas_price=Wei(exponential_scaling_config["max_gas_price"]),
            time_duration=120,
        )

        self.exponentialScalingFast = ExponentialScalingStrategy(
            initial_gas_price=self.fast.get_gas_price(),
            max_gas_price=Wei(exponential_scaling_config["max_gas_price"]),
            time_duration=60,
        )

    def set_default(self, strategy):
        gas_price(strategy)

    def gas_cost(self, gas_estimate):
        """
        total gas cost of estimate in wei
        """
        return Web3.toWei(
            Web3.fromWei(self.fast.get_gas_price(), "gwei") * gas_estimate, "gwei"
        )

    def set_default_for_active_chain(self):
        chain = network_manager.get_active_network()
        if chain == "eth":
            self.set_default(self.exponentialScaling)
        elif chain == "bsc":
            self.set_default(self.bsc_static)

    def optimal_price(self):
        return min(self.fast.get_gas_price(), self.analyzed.mode)


gas_strategies = GasStrategies()
gas_strategies.set_default(gas_strategies.fast)
