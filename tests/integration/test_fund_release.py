from operator import itemgetter
from scripts.systems.badger_system import BadgerSystem
from tests.helpers import getTokenMetadata
from tests.sett.helpers.simulation import take_rewards_action

import brownie
import pytest
from brownie import *
from brownie.test import given, strategy
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.proxy_utils import deploy_proxy
from helpers.registry import whale_registry
from helpers.time_utils import daysToSeconds, hours
from scripts.deploy.deploy_badger import main
from tests.conftest import badger_single_sett
from tests.sett.helpers.snapshots import (
    confirm_deposit,
    confirm_earn,
    confirm_harvest,
    confirm_tend,
    confirm_withdraw,
    sett_snapshot,
)
from helpers.utils import approx
from config.badger_config import badger_config, multisig_config
from rich.console import Console

console = Console()

"""
Test emission schedules of DAO Timelock & Dev Vesting
"""
def test_team_vesting(badger_prod: BadgerSystem):
    badger = badger_prod
    deployer = badger.deployer
    multisig = badger.devMultisig
    teamVesting = badger.teamVesting
    daoTimelock = badger.daoBadgerTimelock
    signer = accounts.at(multisig_config.owners[0], force=True)

    convert_to_test_mode(multisig)
    
    # Should not be able to claim locked token
    with brownie.reverts("smart-timelock/only-beneficiary"):
        teamVesting.claimToken(badger.token, {'from': deployer})

    # with brownie.reverts("smart-timelock/no-locked-token-claim"):
    tx = exec_direct(
            badger.devMultisig,
            {
                "to": teamVesting,
                "data": teamVesting.claimToken.encode_input(badger.token),
            },
            signer,
        )
    assert len(tx.events['ExecutionFailure']) > 0


    # Should not be able to release tokens before unlock time
    tx = exec_direct(
            badger.devMultisig,
            {
                "to": teamVesting,
                "data": teamVesting.release.encode_input(),
            },
            signer,
        )
    assert len(tx.events['ExecutionFailure']) > 0


    with brownie.reverts("TokenVesting: no tokens are due"):
        teamVesting.release({'from': deployer})
    
        chain.sleep(daysToSeconds(15))

    chain.sleep(daysToSeconds(15))
    chain.mine()

    # Should not be able to claim locked token
    with brownie.reverts("smart-timelock/only-beneficiary"):
        teamVesting.claimToken(badger.token, {'from': deployer})

    # Should not be able to release tokens before unlock time
    #with brownie.reverts("TokenVesting: no tokens are due"):
    tx = exec_direct(
            badger.devMultisig,
            {
                "to": teamVesting,
                "data": teamVesting.release.encode_input(),
            },
            signer,
        )
    assert len(tx.events['ExecutionFailure']) > 0

    with brownie.reverts("TokenVesting: no tokens are due"):
        teamVesting.release({'from': deployer})

    chain.sleep(daysToSeconds(15))
    chain.mine()
    
    if chain.time() < teamVesting.cliff():
        chain.sleep(teamVesting.cliff() - chain.time())
        chain.mine()
    
    # Should be able to release 1st month after cliff
    preBalance = badger.token.balanceOf(multisig)
    totalLocked = badger_config.founderRewardsAmount

    vestStart = teamVesting.start()
    vestDuration = teamVesting.duration()
    vestEnd = vestStart + vestDuration

    assert chain.time() >= teamVesting.cliff()

    tx = exec_direct(
        multisig,
        {
            "to": teamVesting,
            "data": teamVesting.release.encode_input(),
        },
        signer,
    )
    print(tx.events)
    assert len(tx.events['ExecutionSuccess']) > 0


    timePassed = chain.time() - vestStart
    proportionPassed = timePassed / vestDuration

    expectReleased = int(totalLocked * proportionPassed)

    postBalance = badger.token.balanceOf(multisig)
    console.log(locals())

    assert approx(preBalance + expectReleased, postBalance, 1)

def test_dao_timelock(badger_prod: BadgerSystem):
    badger = badger_prod
    deployer = badger.deployer
    multisig = badger.devMultisig
    daoTimelock = badger.daoBadgerTimelock

    assert badger.token.balanceOf(daoTimelock) == badger_config.tokenLockParams.badgerLockAmount
    
    with brownie.reverts("TokenTimelock: current time is before release time"):
        daoTimelock.release({'from': deployer})
    if badger_config.globalStartTime - chain.time() > 0:
        chain.sleep(badger_config.globalStartTime - chain.time())
    chain.sleep(daysToSeconds(15))
    chain.mine()

    with brownie.reverts("TokenTimelock: current time is before release time"):
        daoTimelock.release({'from': deployer})

    chain.sleep(daysToSeconds(15) + 1)
    chain.mine()

    # Should be able to release after 30 days
    preBalance = badger.token.balanceOf(badger.dao.agent)
    totalLocked = badger_config.tokenLockParams.badgerLockAmount
    expectReleased = badger.token.balanceOf(daoTimelock)

    console.log(locals())

    assert chain.time() >= daoTimelock.releaseTime()

    assert expectReleased == totalLocked

    daoTimelock.release({'from': deployer})
    postBalance = badger.token.balanceOf(badger.dao.agent)

    assert approx(preBalance + expectReleased, postBalance, 1)