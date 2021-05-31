from brownie import interface


class CompoundSystem:
    def __init__(self, registry):
        self.registry = registry
        self.comptroller = interface.IComptroller(registry.compound.comptroller)

    def ctoken(self, name):
        if not name in self.registry.compound.cTokens:
            raise Exception(f"No cToken found for key {name}")
        return interface.ICToken(self.registry.compound.cTokens[name])
