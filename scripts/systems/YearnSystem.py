from brownie import interface


class YearnSystem:
    def __init__(self, chain_registry):
        self.chain_registry = chain_registry

    def registry(self):
        return interface.RegistryAPI(self.chain_registry.yearn.registry)

    def experimental_vault_by_key(self, key):
        if not key in self.chain_registry.yearn.experimental_vaults:
            raise Exception("Token with key {} not found in registry".format(key))

        address = self.chain_registry.yearn.experimental_vaults[key]
        return self.vault_by_address(address)

    def vault_by_address(self, address):
        return interface.VaultAPI(address)
