from brownie import interface


class TokenSystem:
    def __init__(self, registry):
        self.registry = registry

    def erc20_by_key(self, key):
        if not key in self.registry.tokens:
            raise Exception("Token with key {} not found in registry".format(key))

        address = self.registry.tokens[key]
        return self.erc20_by_address(address)

    def erc20_by_address(self, address):
        return interface.IERC20(address)
