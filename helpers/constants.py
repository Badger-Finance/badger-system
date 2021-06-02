from brownie import *

AddressZero = "0x0000000000000000000000000000000000000000"
MaxUint256 = str(int(2 ** 256 - 1))
EmptyBytes32 = "0x0000000000000000000000000000000000000000000000000000000000000000"

DEFAULT_ADMIN_ROLE = (
    "0x0000000000000000000000000000000000000000000000000000000000000000"
)

TOKEN_LOCKER_ROLE = web3.keccak(text="TOKEN_LOCKER_ROLE").hex()
ROOT_UPDATER_ROLE = web3.keccak(text="ROOT_UPDATER_ROLE").hex()
GUARDIAN_ROLE = web3.keccak(text="GUARDIAN_ROLE").hex()
APPROVED_STAKER_ROLE = web3.keccak(text="APPROVED_STAKER_ROLE").hex()
PAUSER_ROLE = web3.keccak(text="PAUSER_ROLE").hex()
UNPAUSER_ROLE = web3.keccak(text="UNPAUSER_ROLE").hex()
DISTRIBUTOR_ROLE = web3.keccak(text="DISTRIBUTOR_ROLE").hex()
ROOT_PROPOSER_ROLE = web3.keccak(text="ROOT_PROPOSER_ROLE").hex()
ROOT_VALIDATOR_ROLE = web3.keccak(text="ROOT_VALIDATOR_ROLE").hex()
APPROVED_ACCOUNT_ROLE = web3.keccak(text="APPROVED_ACCOUNT_ROLE").hex()

DIGG = "0x798D1bE841a82a273720CE31c822C61a67a601C3"
BADGER = "0x3472A5A71965499acd81997a54BBA8D852C6E53d"
FARM = "0xa0246c9032bC3A600820415aE600c6388619A14D"
XSUSHI = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"

MAX_BOOST = 3
DIGG_SETTS = ["native.uniDiggWbtc", "native.sushiDiggWbtc", "native.digg"]
BADGER_SETTS = ["native.badger", "native.uniBadgerWbtc", "native.sushiBadgerWbtc"]
NATIVE_DIGG_SETTS = ["native.uniDiggWbtc", "native.sushiDiggWbtc"]
NON_NATIVE_SETTS = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.sushiWbtcEth",
    "harvest.renCrv",
    "yearn.wbtc",
    "experimental.sushiIBbtcWbtc",
]

SETT_BOOST_RATIOS = {
    "native.uniDiggWbtc": 0.5,
    "native.sushiDiggWbtc": 0.5,
    "native.uniBadgerWbtc": 0.5,
    "native.sushiBadgerWbtc": 0.5,
    "native.badger": 1,
    "native.digg": 1,
    "native.renCrv": 1,
    "native.sbtcCrv": 1,
    "native.tbtcCrv": 1,
    "harvest.renCrv": 1,
    "native.sushiWbtcEth": 1,
    "yearn.wbtc": 1,
    "experimental.sushiIBbtcWbtc": 1,
}
