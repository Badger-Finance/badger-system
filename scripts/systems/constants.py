from enum import Enum


# Types of Setts
class SettType(Enum):
    DEFAULT = 1
    DIGG = 2


# Constant withdrawal fee (in bps) for testing.
WITHDRAWAL_FEE = 75


# Types of sync fee strategies.
class SyncFeeType(Enum):
    # CONFIG fees are synced from config.
    CONFIG = 1
    # ZERO fees are applied to all setts/strategies.
    ZERO = 2
    # CONSTANT fees are hard coded and applied to all setts/strategies.
    CONSTANT = 2

