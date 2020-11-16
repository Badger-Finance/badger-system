import pytest
from brownie import * 
from dotmap import DotMap
from tests.badger_geyser.geyser_helpers import *
from utils.time_utils import *
import time


defaultParams = DotMap(
  maxUnlockSchedules= 10,
  startBonus= 100,
  bonusPeriod= 1,
  initialSharesPerToken= 10 ** 6,
  globalStartTime= 0,
  founderPercentage= 0,
)

timeBonusParams = DotMap(
  maxUnlockSchedules= 10,
  startBonus= 50,
  bonusPeriod= 86400,
  initialSharesPerToken= 10 ** 6,
  globalStartTime= 0,
  founderPercentage= 0,
)

founderRewardsParams = DotMap(
  maxUnlockSchedules= 10,
  startBonus= 50,
  bonusPeriod= 86400,
  initialSharesPerToken= 10 ** 6,
  globalStartTime= 0,
  founderPercentage= 10,
)

badgerParams = DotMap(
  maxUnlockSchedules= 10,
  startBonus= 33,
  bonusPeriod= days_to_seconds(63),
  initialSharesPerToken= 10 ** 6,
  globalStartTime= 0,
  founderPercentage= 10,
)

def setupContractsAndAccounts(params):
    maxUnlockSchedules, startBonus, bonusPeriod, initialSharesPerToken, globalStartTime, founderPercentage = params

    accounts = chain.getUserAccounts()
    owner = web3.utils.toChecksumAddress(accounts[0])
    anotherAccount = web3.utils.toChecksumAddress(accounts[8])

    userPercentage = 100 - founderPercentage

    ampl = Contract.from_abi(address=)
    ampl.initialize(owner)
    ampl.setMonetaryPolicy(owner)

    dist = BadgerGeyser.new(
        ampl.address,
        ampl.address,
        maxUnlockSchedules,
        startBonus,
        bonusPeriod,
        initialSharesPerToken,
        globalStartTime,
        owner,
        founderPercentage
    )

    ampl.transfer(anotherAccount, AMPL(50000))
    ampl.approve(dist.address, AMPL(50000), { 'from':  anotherAccount })
    ampl.approve(dist.address, AMPL(50000), { 'from':  owner })

    return DotMap(
        owner= owner,
        anotherAccount= anotherAccount,
        ampl= ampl,
        dist= dist,
        founderPercentage= founderPercentage,
        userPercentage= userPercentage,
    )
