import requests
from brownie import *
import os


API_KEY = os.getenv("GASSTATION_KEY")


class EthConfig:
    def __init__(self):
        self.gasPrice = 0
        self.gasPriceMax = Wei("100 gwei")

    def fetch_gas_price(self, speed="fast"):
        response = requests.get(
            f"https://ethgasstation.info/api/ethgasAPI.json?api-key={API_KEY}"
        )
        data = response.json()
        self.gasPrice = Wei(str(int(data["fast"]) / 10) + " gwei")
        print("gasPrice ", self.gasPrice)

        # Defend against massive gas prices from API bugs
        assert self.gasPrice <= self.gasPriceMax
        return self.gasPrice


eth_config = EthConfig()
