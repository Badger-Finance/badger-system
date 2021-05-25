from helpers.registry.ChainRegistry import ChainRegistry
from dotmap import DotMap


matic = DotMap(
    childChainManager="0xA6FA4fB5f76172d178d61B04b0ecd319C5d1C0aa",
)

matic_registry = ChainRegistry(
    matic=matic,
)
