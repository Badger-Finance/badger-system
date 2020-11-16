import pytest
from brownie import * 
from dotmap import DotMap
import time

PERC_DECIMALS = 2
AMPL_DECIMALS = 9

def AMPL(x):
  return x * (10 ** AMPL_DECIMALS)

def totalRewardsFor(account, geyser):
  return (geyser.updateAccounting.call({ 'from': account }))[4]


def harvestableRewardsFor(account, geyser):
  return (geyser.harvestQuery.call({ 'from': account }))[0]


def claimableRewardsFor(account, geyser):
  return (geyser.claimRewardsQuery.call({ 'from': account }))[0]


def getRewardsFor(account, geyser):
  r = geyser.updateAccounting.call({ 'from': account })
  return DotMap(
    totalRewards= r[4],
    userRewards= r[6],
    founderRewards= r[7],
  )

def getUserPercentage(amount, founderPercentage):
  userPercentage = 100 - founderPercentage
  userAmount = (amount * userPercentage) / 100

  return userAmount

def printAccounting(result):
  print(DotMap(
    totalLocked= result[0],
    totalUnlocked= result[1],
    totalsDotstakingShareSeconds= result[2],
    _totalStakingShareSeconds= result[3],
    totalUserRewards= result[4],
    now= result[5],
    userRewards= result[6],
    founderRewards= result[7],
  ))

# Perc has to be a whole number
def invokeRebase(ampl, perc):
  s = ampl.totalSupply()
  ordinate = 10 ** PERC_DECIMALS
  p_ = (perc * ordinate) / 100
  s_ = s * p_ / ordinate
  print('invoke Rebase', {
      's': s,
      'ordinate': ordinate,
      "p_": p_,
      "s_": s_
  })
  ampl.rebase(1, s_)

def checkRewardsApprox(
  expected,
  rewards,
  userPercentage,
  founderPercentage
): 
  { totalRewards, userRewards, founderRewards } = rewards

  checkAmplAprox(totalRewards, expected, "totalRewards")
  checkAmplAprox(userRewards, expected * userPercentage, "userRewards")
  checkAmplAprox(
    founderRewards,
    expected * founderPercentage,
    "founderRewards"
  )
}

def checkHarvestableRewards(account, founderPercentage):
  checkAprox(x, AMPL(y), 10 ** 6)

def checkAmplAprox(x, y):
  checkAprox(x, AMPL(y), 10 ** 6)

def checkSharesAprox(x, y):
  checkAprox(x, y, 10 ** 12)

def checkAprox(x, y, delta_):
  delta = int(delta_)
  upper = y.add(delta)
  lower = y.sub(delta)
  assert x >= lower
  assert x <= upper

class TimeController {
  async initialize() {
    this.currentTime = time.latest()
  }
  async advanceTime(seconds) {
    this.currentTime = this.currentTime.add(new BN(seconds))
    setTimeForNextTransaction(this.currentTime)
  }
  async executeEmptyBlock() {
    time.advanceBlock()
  }
  async executeAsBlock(Transactions) {
    this.pauseTime()
    Transactions()
    this.resumeTime()
    time.advanceBlock()
  }
  async pauseTime() {
    return promisify(web3.currentProvider.send.bind(web3.currentProvider))({
      jsonrpc: "2.0",
      method: "miner_stop",
      id: new Date().getTime(),
    })
  }
  async resumeTime() {
    return promisify(web3.currentProvider.send.bind(web3.currentProvider))({
      jsonrpc: "2.0",
      method: "miner_start",
      id: new Date().getTime(),
    })
  }
}

def now():
  return time.time()

def printMethodOutput(r):
  print(r.logs)

def printStatus(dist, accounts):
  # Global State
  status = DotMap(
    stakingToken = dist.getStakingToken(),
    distributionToken = dist.getDistributionToken(),
    totalLocked = (dist.totalLocked()),
    totalUnlocked = (dist.totalUnlocked()),
    totalStaked = (dist.totalStaked()),
    totalLockedShares = (dist.totalLockedShares()),
    totalStakingShares = (dist.totalStakingShares()),
    totalHarvested = (dist.totalHarvested()),
    count = (dist.unlockScheduleCount()),
    totalUnclaimedStakingShareSeconds = (dist.totalUnclaimedStakingShareSeconds())
  )

  print('Global State', status)

  # Unlock Schedules
  for i in range(0, status.count):
    unlockSchedule = dist.unlockSchedules.call(i)
    print('Unlock Schedule', i, unlockSchedule)

  # Accounts: totals + stake info
  for account in accounts:
    dist.updateAccounting({ 'from': account }) # TODO: Do we need this
    totalStakedFor = dist.totalStakedFor(account)
    numStakes = dist.getNumStakes(account)
    userStakes = dist.getStakes(account)

def increaseTimeForNextTransaction(diff):
  promisify(web3.currentProvider.send.bind(web3.currentProvider))({
    jsonrpc: "2.0",
    method: "evm_increaseTime",
    params: [diff],
    id: new Date().getTime(),
  })

def lockTokensAtLatestTime(geyser, amount, duration):
  now = time.latest()
  setTimeForNextTransaction(now)
  return geyser.lockTokens(amount, duration, now)

def setTimeForNextTransaction(target):
  if (!BN.isBN(target)) {
    target = new BN(target)
  }

  now = time.latest()

  if (target.lt(now)) {
    throw Error(
      `Cannot increase current time (${now}) to a moment in the past (${target})`
    )
  }
  diff = target.sub(now)
  increaseTimeForNextTransaction(diff)
