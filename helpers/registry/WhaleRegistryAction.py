from dotmap import DotMap
from enum import Enum


class WhaleRegistryAction(Enum):
    DISTRIBUTE_FROM_EOA = (0,)
    DISTRIBUTE_FROM_CONTRACT = (1,)
    POPULATE_NEW_SUSHI_LP = 2
