from brownie import *


class DiggUtils:
    def __init__(self):
        self.digg = interface.IDigg("0x798D1bE841a82a273720CE31c822C61a67a601C3")
        self.sharesPerFragment = self.digg._sharesPerFragment()
        self.initalShares = self.digg._initialSharesPerFragment()

    def sharesToFragments(self, amount):
        if amount == 0:
            return 0
        else:
            return self.sharesPerFragment / int(amount)


diggUtils = DiggUtils()
