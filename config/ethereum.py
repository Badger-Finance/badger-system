import requests
from brownie import *
class EthConfig:
    def __init__(self):
        self.gasPrice = 0
        self.gasPriceMax = Wei("100 gwei")

    # TODO: Remove API Key
    def fetch_gas_price(self, speed="fast"):
        response = requests.get("https://ethgasstation.info/api/ethgasAPI.json?api-key=e7fec12004fbbb558ed0a612131a97f68ddfe83d31a29ac440fc2f11c386")
        data = response.json()
        self.gasPrice = Wei(str(int(data['fast']) / 10)+ " gwei")
        print('gasPrice ', self.gasPrice)

        # Defend against massive gas prices from API bugs
        assert self.gasPrice <= self.gasPriceMax
        return self.gasPrice

eth_config = EthConfig()






