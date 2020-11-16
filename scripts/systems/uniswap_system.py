from brownie import *
from helpers.constants import AddressZero
from helpers.registry import registry
def connect_curve(registry):
    return UniswapSystem(registry.uniswap)

class UniswapSystem:
    def _init__(self, uniswap):
        self.uniswap = uniswap
        self.factory = Contract.from_abi(
            "UniswapV2Factory",
            web3.toChecksumAddress(uniswap.addresses.factoryV2),
            uniswap.artifacts["UniswapV2Factory"],
        ),
        self.router = Contract.from_abi(
            "UniswapV2Router",
            web3.toChecksumAddress(uniswap.addresses.routerV2),
            uniswap.artifacts["UniswapV2Router"],
        )
    
    def getPair(self, tokenA, tokenB):
        """
        Return pair token. Throws error if pair doesn't exist.
        """
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return Contract.from_abi("UniswapV2Pair", pairAddress, self.uniswap.artifacts["UniswapV2Pair"])

    def hasPair(self, tokenA, tokenB):
        """
        Return true if pair exists
        """ 
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return pairAddress != AddressZero
