from brownie import interface

from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry
from helpers.constants import AddressZero
from .BaseProvisioner import BaseProvisioner


class WbtcIbBtcLpProvisioner(BaseProvisioner):
    def __init__(self, manager, isUniswap=False):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
            registry.whales.bSbtcCrv,
            registry.whales.bTbtcCrv,
            registry.whales.bRenCrv,
        ]
        self.badgerSettPeak = interface.IPeak(
            registry.defidollar.addresses.badgerSettPeak
        )
        self.core = interface.ICore(registry.defidollar.addresses.core)
        self.isUniswap = isUniswap

    def _distributeWant(self, users) -> None:
        # Turn off guestlist.
        self.core.setGuestList(AddressZero, {"from": self.core.owner()})

        # Generate lp tokens for users.
        for user in users:
            # Mint ibBTC using sett lp tokens.
            self._mintIbBtc(user)
            swap = UniswapSystem()
            if not self.isUniswap:
                swap = SushiswapSystem()
            # Generate lp tokens.
            swap.addMaxLiquidity(
                registry.tokens.ibbtc,
                registry.tokens.wbtc,
                user,
            )

    def _mintIbBtc(self, user) -> None:
        for pool in registry.defidollar.pools:
            settToken = interface.ERC20(pool.sett)
            balance = settToken.balanceOf(user)
            settToken.approve(self.badgerSettPeak, balance, {"from": user})
            self.badgerSettPeak.mint(pool.id, balance, [], {"from": user})
