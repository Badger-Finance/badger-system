from brownie import (
    web3,
    interface,
    Contract
)

from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.registry import registry
from .BaseProvisioner import BaseProvisioner


class SushiWbtcIbBtcLpOptimizerProvisioner(BaseProvisioner):
    def __init__(self, manager):
        super().__init__(manager)
        # Whales are hard coded for now.
        self.whales = [
            registry.whales.wbtc,
            registry.whales.bSbtcCrv,
            registry.whales.bTbtcCrv,
            registry.whales.bRenCrv,
        ]
        abi = registry.defidollar.artifacts["BadgerSettPeak"]
        self.badgerSettPeak = Contract.from_abi(
            "BadgerSettPeak",
            registry.defidollar.addresses.badgerSettPeak,
            abi,
        )

    def _distributeWant(self, users) -> None:
        # Generate lp tokens for users.
        for user in users:
            # Mint ibBTC using sett lp tokens.
            self._mintIbBtc(user)
            sushiswap = SushiswapSystem()
            # Generate lp tokens.
            sushiswap.addMaxLiquidity(
                registry.tokens.ibbtc,
                registry.tokens.wbtc,
                user,
            )

    def _mintIbBtc(self, user) -> None:
        for pool in registry.defidollar.pools:
            settToken = interface.ERC20(pool.sett)
            balance = settToken.balanceOf(user)
            settToken.approve(self.badgerSettPeak, balance, {"from": user})
            self.badgerSettPeak.mint(pool.id, balance, {"from": user})
