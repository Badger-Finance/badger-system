from brownie import *
from helpers.constants import DIGG


class DiggUtils:
    def __init__(self):
        self.digg = interface.IDigg(DIGG)
        self.sharesPerFragment = self.digg._sharesPerFragment()
        self.initialShares = self.digg._initialSharesPerFragment()

    def sharesToFragments(self, shares):
        if shares == 0:
            return 0
        return self.sharesPerFragment / shares


diggUtils = DiggUtils()
