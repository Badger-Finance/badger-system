from scripts.systems.CompoundSystem import CompoundSystem
from scripts.systems.AaveSystem import AaveSystem
from scripts.systems.YearnSystem import YearnSystem
from scripts.systems.TokenSystem import TokenSystem


class ChainRegistry:
    def __init__(
        self,
        curve=None,
        uniswap=None,
        open_zeppelin=None,
        aragon=None,
        sushiswap=None,
        sushi=None,
        gnosis_safe=None,
        onesplit=None,
        pickle=None,
        harvest=None,
        tokens=None,
        whales=None,
        multicall=None,
        multisend=None,
        pancake=None,
        badger=None,
        yearn=None,
        aave=None,
        compound=None,
        defidollar=None,
    ):
        self.curve = curve
        self.uniswap = uniswap
        self.open_zeppelin = open_zeppelin
        self.aragon = aragon
        self.sushiswap = sushiswap
        self.sushi = sushi
        self.gnosis_safe = gnosis_safe
        self.onesplit = onesplit
        self.pickle = pickle
        self.harvest = harvest
        self.tokens = tokens
        self.whales = whales
        self.multicall = multicall
        self.multisend = multisend
        self.pancake = pancake
        self.badger = badger
        self.yearn = yearn
        self.aave = aave
        self.compound = compound
        self.defidollar = defidollar

    def yearn_system(self) -> YearnSystem:
        if self.yearn == None:
            raise Exception("No yearn system registered")
        return YearnSystem(self)

    def token_system(self) -> TokenSystem:
        if self.tokens == None:
            raise Exception("No yearn system registered")
        return TokenSystem(self)

    def aave_system(self) -> AaveSystem:
        if self.aave == None:
            raise Exception("No aave system registered")
        return AaveSystem(self)

    def compound_system(self) -> CompoundSystem:
        if self.aave == None:
            raise Exception("No aave system registered")
        return CompoundSystem(self)
