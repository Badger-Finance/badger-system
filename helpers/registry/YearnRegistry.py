class YearnRegistry:
    def __init__(self, registry=None, experimental_vaults=None):
        self.registry = registry
        self.experimental_vaults = experimental_vaults

    def get_experimental_vault(self, key):
        return self.experimental_vaults[key]
