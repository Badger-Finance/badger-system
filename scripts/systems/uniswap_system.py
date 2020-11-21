from helpers.utils import Eth
from brownie import *
from helpers.constants import AddressZero, MaxUint256
from helpers.registry import registry

uniswap = registry.uniswap


def connect_uniswap():
    return UniswapSystem()


class UniswapSystem:
    def __init__(self):
        self.uniswap = uniswap
        self.factory = interface.IUniswapV2Factory(
            web3.toChecksumAddress(uniswap.factoryV2)
        )
        self.router = interface.IUniswapRouterV2(
            web3.toChecksumAddress(uniswap.routerV2)
        )

    def createPair(self, tokenA, tokenB, signer):
        tx = self.factory.createPair(tokenA, tokenB, {"from": signer})
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return interface.IUniswapV2Pair(pairAddress)

    def addMaxLiquidity(self, tokenA, tokenB, signer):
        # TODO: Determine if passed in contracts or addresses and process accordingly. Should be able to accept both in any combinantion. Currently expects contracts
        tokenA.approve(self.router, MaxUint256, {"from": signer})
        tokenB.approve(self.router, MaxUint256, {"from": signer})

        balanceA = tokenA.balanceOf(signer) // 2
        balanceB = tokenB.balanceOf(signer) // 2

        print(balanceA, balanceB)

        assert balanceA > 0
        assert balanceB > 0

        return self.router.addLiquidity(
            tokenA.address,
            tokenB.address,
            balanceA,
            balanceB,
            0,
            0,
            signer,
            chain.time() + 1000,
            {"from": signer},
        )

    def getPair(self, tokenA, tokenB):
        """
        Return pair token. Throws error if pair doesn't exist.
        """

        pairAddress = self.factory.getPair(tokenA, tokenB)
        return Contract.from_abi(
            "UniswapV2Pair", pairAddress, self.uniswap.artifacts["UniswapV2Pair"]["abi"]
        )

    def hasPair(self, tokenA, tokenB):
        """
        Return true if pair exists
        """
        print("self.factory", self.factory)
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return pairAddress != AddressZero
