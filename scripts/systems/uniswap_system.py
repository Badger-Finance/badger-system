from helpers.utils import Eth
from brownie import *
from helpers.constants import AddressZero, MaxUint256
from helpers.registry import registry


class UniswapSystem:
    def __init__(self):
        self.contract_registry = registry.uniswap
        self.factory = interface.IUniswapV2Factory(
            web3.toChecksumAddress(self.contract_registry.factoryV2)
        )
        self.router = interface.IUniswapRouterV2(
            web3.toChecksumAddress(self.contract_registry.routerV2)
        )

    def createPair(self, tokenA, tokenB, signer):
        tx = self.factory.createPair(tokenA, tokenB, {"from": signer})
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return interface.IUniswapV2Pair(pairAddress)

    def addMaxLiquidity(self, tokenA, tokenB, signer):
        print("self", tokenA, tokenB)
        tokenA = interface.IERC20(tokenA)
        tokenB = interface.IERC20(tokenB)

        balanceA = tokenA.balanceOf(signer) // 2
        balanceB = tokenB.balanceOf(signer) // 2

        print(balanceA, balanceB)

        assert balanceA > 0
        assert balanceB > 0

        # TODO: Determine if passed in contracts or addresses and process accordingly. Should be able to accept both in any combinantion. Currently expects contracts
        tokenA.approve(self.router, MaxUint256, {"from": signer})
        tokenB.approve(self.router, MaxUint256, {"from": signer})

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
        return interface.IUniswapV2Pair(pairAddress)

    def hasPair(self, tokenA, tokenB):
        """
        Return true if pair exists
        """
        print("self.factory", self.factory)
        pairAddress = self.factory.getPair(tokenA, tokenB)
        return pairAddress != AddressZero
