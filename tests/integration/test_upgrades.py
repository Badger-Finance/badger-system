from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config

"""
badger.contracts = [
    badger.badgerTree,
    badger.badgerHunt,
    badger.rewardsEscrow,
    badger.sett.native.controller,
    badger.sett.harvest.controller,
    badger.sett.pickle.controller,
    badger.sett.native.badger,
    badger.sett.native.renCrv,
    badger.sett.native.sBtcCrv,
    badger.sett.native.tBtcCrv,
    badger.sett.harvest.renCrv,
    badger.sett.pickle.renCrv,
    badger.sett.native.strategies.badger,
    badger.sett.native.strategies.renCrv,
    badger.sett.native.strategies.sBtcCrv,
    badger.sett.native.strategies.tBtcCrv,
    badger.sett.harvest.strategies.renCrv,
    badger.sett.pickle.strategies.renCrv,
    badger.sett.rewards.badger,
    badger.teamVesting,
    badger.daoBadgerTimelock,
    badger.pools.sett.native.renCrv,
    badger.pools.sett.native.sBtcCrv,
    badger.pools.sett.native.tBtcCrv,
    badger.pools.sett.harvest.renCrv,
    badger.pools.sett.pickle.renCrv,
]
"""

def test_confirm_contract_admins(badger):
    owner = badger.deployer

    assert badger.devProxyAdmin.owner() == owner

    # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
    for contract in badger.contracts:
        assert (
            badger.devProxyAdmin.getProxyImplementation(contract)
            == badger.logic.BadgerTree
        )
