from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))
EmptyBytes32 = "0x0000000000000000000000000000000000000000000000000000000000000000"

DEFAULT_ADMIN_ROLE = (
    "0x0000000000000000000000000000000000000000000000000000000000000000"
)


class RoleRegistry:
    def __init__(self):
        self.roles = {}

    def add_role(self, name):
        encoded = web3.keccak(text=name).hex()
        self.roles[name] = encoded


# Approved Contract Roles
APPROVED_STAKER_ROLE = web3.keccak(text="APPROVED_STAKER_ROLE").hex()
APPROVED_SETT_ROLE = web3.keccak(text="APPROVED_SETT_ROLE").hex()
APPROVED_STRATEGY_ROLE = web3.keccak(text="APPROVED_STRATEGY_ROLE").hex()

PAUSER_ROLE = web3.keccak(text="PAUSER_ROLE").hex()
UNPAUSER_ROLE = web3.keccak(text="UNPAUSER_ROLE").hex()
GUARDIAN_ROLE = web3.keccak(text="GUARDIAN_ROLE").hex()

# BadgerTree Roles
ROOT_UPDATER_ROLE = web3.keccak(text="ROOT_UPDATER_ROLE").hex()
ROOT_PROPOSER_ROLE = web3.keccak(text="ROOT_PROPOSER_ROLE").hex()
ROOT_VALIDATOR_ROLE = web3.keccak(text="ROOT_VALIDATOR_ROLE").hex()

# UnlockSchedule Roles
TOKEN_LOCKER_ROLE = web3.keccak(text="TOKEN_LOCKER_ROLE").hex()

# Keeper Roles
KEEPER_ROLE = web3.keccak(text="KEEPER_ROLE").hex()
EARNER_ROLE = web3.keccak(text="EARNER_ROLE").hex()

# External Harvester Roles
SWAPPER_ROLE = web3.keccak(text="SWAPPER_ROLE").hex()
DISTRIBUTOR_ROLE = web3.keccak(text="DISTRIBUTOR_ROLE").hex()

APPROVED_ACCOUNT_ROLE = web3.keccak(text="APPROVED_ACCOUNT_ROLE").hex()

role_registry = RoleRegistry()

role_registry.add_role("APPROVED_STAKER_ROLE")
role_registry.add_role("APPROVED_SETT_ROLE")
role_registry.add_role("APPROVED_STRATEGY_ROLE")

role_registry.add_role("PAUSER_ROLE")
role_registry.add_role("UNPAUSER_ROLE")
role_registry.add_role("GUARDIAN_ROLE")

role_registry.add_role("ROOT_UPDATER_ROLE")
role_registry.add_role("ROOT_PROPOSER_ROLE")
role_registry.add_role("ROOT_VALIDATOR_ROLE")

role_registry.add_role("TOKEN_LOCKER_ROLE")

role_registry.add_role("KEEPER_ROLE")
role_registry.add_role("EARNER_ROLE")

role_registry.add_role("SWAPPER_ROLE")
role_registry.add_role("DISTRIBUTOR_ROLE")

role_registry.add_role("APPROVED_ACCOUNT_ROLE")


DIGG = "0x798D1bE841a82a273720CE31c822C61a67a601C3"
BADGER = "0x3472A5A71965499acd81997a54BBA8D852C6E53d"
FARM = "0xa0246c9032bC3A600820415aE600c6388619A14D"
XSUSHI = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"
DFD = "0x20c36f062a31865bED8a5B1e512D9a1A20AA333A"
BCVXCRV = "0x2B5455aac8d64C14786c3a29858E43b5945819C0"
BCVX = "0x53C8E199eb2Cb7c01543C137078a038937a68E40"
PNT = "0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD"
BOR = "0x3c9d6c1C73b31c837832c72E04D3152f051fc1A9"

TOKENS_TO_CHECK = {
    "Badger": BADGER,
    "Digg": DIGG,
    "Farm": FARM,
    "xSushi": XSUSHI,
    "Dfd": DFD,
    "bCvxCrv": BCVXCRV,
    "bCvx": BCVX,
    "Pnt": PNT,
    "Bor": BOR,
}

BADGER_TREE = "0x660802Fc641b154aBA66a62137e71f331B6d787A"

PEAK_ADDRESSES = [
    "0x825218beD8BE0B30be39475755AceE0250C50627",
    "0x41671BA1abcbA387b9b2B752c205e22e916BE6e3",
]

DIGG_SETTS = ["native.uniDiggWbtc", "native.sushiDiggWbtc", "native.digg"]
BADGER_SETTS = ["native.badger", "native.uniBadgerWbtc", "native.sushiBadgerWbtc"]
NATIVE_DIGG_SETTS = ["native.uniDiggWbtc", "native.sushiDiggWbtc"]



REWARDS_BLACKLIST = {
    "0x19d97d8fa813ee2f51ad4b4e04ea08baf4dffc28": "Badger Vault",
    "0xb65cef03b9b89f99517643226d76e286ee999e77": "Badger Dev Multisig",
    "0x8b950f43fcac4931d408f1fcda55c6cb6cbf3096": "Cream bBadger",
    "0x0a54d4b378c8dbfc7bc93be50c85debafdb87439": "Sushiswap bBadger/Weth",
}

STAKE_RATIO_RANGES = list(
    [
        (0, 1),
        (0.001, 2),
        (0.0025, 5),
        (0.005, 10),
        (0.01, 20),
        (0.025, 50),
        (0.05, 100),
        (0.075, 150),
        (0.10, 200),
        (0.15, 300),
        (0.2, 400),
        (0.25, 500),
        (0.3, 600),
        (0.4, 800),
        (0.5, 1000),
        (0.6, 1200),
        (0.7, 1400),
        (0.8, 1600),
        (0.9, 1800),
        (1, 2000),
    ]
)

SETT_INFO = {
    "0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28": {
        "type": "native",
        "ratio": 1,
    },
    "0x235c9e24D3FB2FAFd58a2E49D454Fdcd2DBf7FF1": {"type": "native", "ratio": 0.5},
    "0x1862A18181346EBd9EdAf800804f89190DeF24a5": {"type": "native", "ratio": 0.5},
    "0x7e7E112A68d8D2E221E11047a72fFC1065c38e1a": {"type": "native", "ratio": 1},
    "0xC17078FDd324CC473F8175Dc5290fae5f2E84714": {"type": "native", "ratio": 0.5},
    "0x88128580ACdD9c04Ce47AFcE196875747bF2A9f6": {"type": "native", "ratio": 0.5},
}
