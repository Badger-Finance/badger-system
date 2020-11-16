const { BN } = require("@openzeppelin/test-helpers");
const { promisify } = require("util");
const { time } = require("@openzeppelin/test-helpers");
const { expect } = require("chai");

const PERC_DECIMALS = 2;
const AMPL_DECIMALS = 9;

const ONE_HOUR = 3600;
const ONE_DAY = 24 * ONE_HOUR;
const ONE_YEAR = 1 * 365 * ONE_DAY;

function $AMPL(x) {
  return new BN(x * 10 ** AMPL_DECIMALS);
}

function daysToSeconds(days) {
  return days * 86400;
}

async function totalRewardsFor(account, geyser) {
  return (await geyser.updateAccounting.call({ from: account }))[4];
}

async function harvestableRewardsFor(account, geyser) {
  return (await geyser.harvestQuery.call({ from: account }))[0];
}

async function claimableRewardsFor(account, geyser) {
  return (await geyser.claimRewardsQuery.call({ from: account }))[0];
}

async function getRewardsFor(account, geyser) {
  const r = await geyser.updateAccounting.call({ from: account });
  return {
    totalRewards: r[4],
    userRewards: r[6],
    founderRewards: r[7],
  };
}

function getUserPercentage(amount, founderPercentage) {
  const userPercentage = 100 - founderPercentage;
  const userAmount = (amount * userPercentage) / 100;

  return userAmount;
}

function printAccounting(result) {
  console.log({
    totalLocked: result[0].toString(),
    totalUnlocked: result[1].toString(),
    totalsDotstakingShareSeconds: result[2].toString(),
    _totalStakingShareSeconds: result[3].toString(),
    totalUserRewards: result[4].toString(),
    now: result[5].toString(),
    userRewards: result[6].toString(),
    founderRewards: result[7].toString(),
  });
}

// Perc has to be a whole number
async function invokeRebase(ampl, perc) {
  const s = await ampl.totalSupply.call();
  const ordinate = 10 ** PERC_DECIMALS;
  const p_ = new BN(parseInt(perc * ordinate)).div(new BN(100));
  const s_ = s.mul(p_).div(new BN(ordinate));
  await ampl.rebase(1, s_);
}

function checkRewardsApprox(
  expected,
  rewards,
  userPercentage,
  founderPercentage
) {
  const { totalRewards, userRewards, founderRewards } = rewards;

  checkAmplAprox(totalRewards, expected, "totalRewards");
  checkAmplAprox(userRewards, expected * userPercentage, "userRewards");
  checkAmplAprox(
    founderRewards,
    expected * founderPercentage,
    "founderRewards"
  );
}

function checkHarvestableRewards(account, founderPercentage) {
  checkAprox(x, $AMPL(y), 10 ** 6, message);
}

function checkAmplAprox(x, y, message = undefined) {
  checkAprox(x, $AMPL(y), 10 ** 6, message);
}

function checkSharesAprox(x, y) {
  checkAprox(x, y, 10 ** 12);
}

function checkAprox(x, y, delta_, message = undefined) {
  const delta = new BN(parseInt(delta_));
  const upper = y.add(delta);
  const lower = y.sub(delta);

  if (message) {
    expect(x, message)
      .to.be.bignumber.at.least(lower)
      .and.bignumber.at.most(upper);
  } else {
    expect(x)
      .to.be.bignumber.at.least(lower)
      .and.bignumber.at.most(upper);
  }
}

class TimeController {
  async initialize() {
    this.currentTime = await time.latest();
  }
  async advanceTime(seconds) {
    this.currentTime = this.currentTime.add(new BN(seconds));
    await setTimeForNextTransaction(this.currentTime);
  }
  async executeEmptyBlock() {
    await time.advanceBlock();
  }
  async executeAsBlock(Transactions) {
    await this.pauseTime();
    Transactions();
    await this.resumeTime();
    await time.advanceBlock();
  }
  async pauseTime() {
    return promisify(web3.currentProvider.send.bind(web3.currentProvider))({
      jsonrpc: "2.0",
      method: "miner_stop",
      id: new Date().getTime(),
    });
  }
  async resumeTime() {
    return promisify(web3.currentProvider.send.bind(web3.currentProvider))({
      jsonrpc: "2.0",
      method: "miner_start",
      id: new Date().getTime(),
    });
  }
}

function now() {
  return Math.floor(Date.now() / 1000).toString();
}

async function printMethodOutput(r) {
  console.log(r.logs);
}

async function printStatus(dist, accounts) {
  // Global State
  const stakingToken = await dist.getStakingToken.call();
  const distributionToken = await dist.getDistributionToken.call();

  const totalLocked = (await dist.totalLocked.call()).toString();
  const totalUnlocked = (await dist.totalUnlocked.call()).toString();
  const totalStaked = (await dist.totalStaked.call()).toString();
  const totalLockedShares = (await dist.totalLockedShares.call()).toString();
  const totalStakingShares = (await dist.totalStakingShares.call()).toString();
  const totalHarvested = (await dist.totalHarvested.call()).toString();
  const count = (await dist.unlockScheduleCount.call()).toNumber();

  const totalUnclaimedStakingShareSeconds = (await dist.totalUnclaimedStakingShareSeconds.call()).toString();

  console.log(`Global State:
    stakingToken: ${stakingToken}
    distributionToken: ${distributionToken}

    totalLocked: ${totalLocked}
    totalUnlocked: ${totalUnlocked}
    totalStaked: ${totalStaked}

    totalLockedShares: ${totalLockedShares}
    totalStakingShares: ${totalStakingShares}
    totalHarvested: ${totalHarvested}

    unlockScheduleCount: ${count}

    totalUnclaimedStakingShareSeconds: ${totalUnclaimedStakingShareSeconds}
  `);

  // Unlock Schedules
  for (let i = 0; i < count; i++) {
    const unlockSchedule = await dist.unlockSchedules.call(i);
    const formatted = formatUnlockSchedule(unlockSchedule);
    console.log(`Unlock Schedule ${i}:
      initialLockedShares: ${formatted.initialLockedShares}
      unlockedShares: ${formatted.unlockedShares}
      lastUnlockTimestampSec: ${formatted.lastUnlockTimestampSec}
      endAtSec: ${formatted.endAtSec}
      durationSec: ${formatted.durationSec}
      startTime: ${formatted.startTime}
    `);
  }

  // Accounts: totals + stake info
  for (const account of accounts) {
    await dist.updateAccounting({ from: account }); //TODO: Do we need this
    const totalStakedFor = (await dist.totalStakedFor.call(account)).toString();
    const numStakes = (await dist.getNumStakes.call(account)).toNumber();

    // Each Stake
    for (let i = 0; i < numStakes; i++) {
      const stake = await dist.getStake.call(account, i);
      const formatted = formatStake(stake);
      const rewardMultiplier = (await dist.getStakeRewardMultiplier.call(
        account,
        i
      )).toString();
      console.log(`Stake ${account} ${i}:
        stakingShares: ${formatted.stakingShares}
        timestampSec: ${formatted.timestampSec}
        lastHarvestTimestampSec: ${formatted.lastHarvestTimestampSec}
        rewardMultiplier: ${rewardMultiplier}
      `);
    }
  }
}

function formatUnlockSchedule(unlockSchedule) {
  return {
    initialLockedShares: unlockSchedule.initialLockedShares.toString(),
    unlockedShares: unlockSchedule.unlockedShares.toString(),
    lastUnlockTimestampSec: unlockSchedule.lastUnlockTimestampSec.toString(),
    endAtSec: unlockSchedule.endAtSec.toString(),
    durationSec: unlockSchedule.durationSec.toString(),
    startTime: unlockSchedule.startTime.toString(),
  };
}

function formatStake(stake) {
  return {
    stakingShares: stake.stakingShares.toString(),
    timestampSec: stake.timestampSec.toString(),
    lastHarvestTimestampSec: stake.lastHarvestTimestampSec.toString(),
  };
}

async function increaseTimeForNextTransaction(diff) {
  await promisify(web3.currentProvider.send.bind(web3.currentProvider))({
    jsonrpc: "2.0",
    method: "evm_increaseTime",
    params: [diff.toNumber()],
    id: new Date().getTime(),
  });
}

async function lockTokensAtLatestTime(geyser, amount, duration) {
  const now = await time.latest();
  await setTimeForNextTransaction(now);
  return await geyser.lockTokens(amount, duration, now);
}

async function setSnapshot() {
  return new Promise((resolve, reject) => {
    web3.currentProvider.send(
      {
        jsonrpc: "2.0",
        method: "evm_snapshot",
        id: new Date().getTime(),
      },
      (err, snapshotId) => {
        if (err) {
          return reject(err);
        }
        return resolve(snapshotId);
      }
    );
  });
}

async function revertSnapshot(id) {
  return new Promise((resolve, reject) => {
    web3.currentProvider.send(
      {
        jsonrpc: "2.0",
        method: "evm_revert",
        params: [id],
        id: new Date().getTime(),
      },
      (err, result) => {
        if (err) {
          return reject(err);
        }
        return resolve(result);
      }
    );
  });
}

async function setTimeForNextTransaction(target) {
  if (!BN.isBN(target)) {
    target = new BN(target);
  }

  const now = await time.latest();

  if (target.lt(now)) {
    throw Error(
      `Cannot increase current time (${now}) to a moment in the past (${target})`
    );
  }
  const diff = target.sub(now);
  increaseTimeForNextTransaction(diff);
}

module.exports = {
  checkAmplAprox,
  checkSharesAprox,
  invokeRebase,
  $AMPL,
  increaseTimeForNextTransaction,
  setTimeForNextTransaction,
  TimeController,
  printMethodOutput,
  printStatus,
  now,
  lockTokensAtLatestTime,
  checkRewardsApprox,
  ONE_HOUR,
  ONE_DAY,
  ONE_YEAR,
  setSnapshot,
  revertSnapshot,
  printAccounting,
  totalRewardsFor,
  getRewardsFor,
  daysToSeconds,
  claimableRewardsFor,
  harvestableRewardsFor,
  getUserPercentage,
};
