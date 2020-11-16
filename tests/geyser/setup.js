const {
  expectRevert,
  expectEvent,
  BN,
  constants,
} = require("@openzeppelin/test-helpers");
const { expect } = require("chai");

const _require = require("app-root-path").require;
const BlockchainCaller = _require("/util/blockchain_caller");
const chain = new BlockchainCaller(web3);
const {
  $AMPL,
  invokeRebase,
  totalRewardsFor,
  getRewardsFor,
  daysToSeconds,
} = _require("/test/helper");

const AmpleforthErc20 = artifacts.require("UFragments");
const BadgerGeyser = artifacts.require("BadgerGeyser");

let owner, anotherAccount, ampl, dist, founderPercentage, userPercentage;

const defaultParams = {
  maxUnlockSchedules: 10,
  startBonus: 100,
  bonusPeriod: 1,
  initialSharesPerToken: 10 ** 6,
  globalStartTime: 0,
  founderPercentage: 0,
};

const timeBonusParams = {
  maxUnlockSchedules: 10,
  startBonus: 50,
  bonusPeriod: 86400,
  initialSharesPerToken: 10 ** 6,
  globalStartTime: 0,
  founderPercentage: 0,
};

const founderRewardsParams = {
  maxUnlockSchedules: 10,
  startBonus: 50,
  bonusPeriod: 86400,
  initialSharesPerToken: 10 ** 6,
  globalStartTime: 0,
  founderPercentage: 10,
};

const badgerParams = {
  maxUnlockSchedules: 10,
  startBonus: 33,
  bonusPeriod: daysToSeconds(63),
  initialSharesPerToken: 10 ** 6,
  globalStartTime: 0,
  founderPercentage: 10,
};

async function setupContractsAndAccounts(params) {
  const {
    maxUnlockSchedules,
    startBonus,
    bonusPeriod,
    initialSharesPerToken,
    globalStartTime,
    founderPercentage,
  } = params;

  const accounts = await chain.getUserAccounts();
  owner = web3.utils.toChecksumAddress(accounts[0]);
  anotherAccount = web3.utils.toChecksumAddress(accounts[8]);

  userPercentage = 100 - founderPercentage;

  ampl = await AmpleforthErc20.new();
  await ampl.initialize(owner);
  await ampl.setMonetaryPolicy(owner);

  dist = await BadgerGeyser.new(
    ampl.address,
    ampl.address,
    maxUnlockSchedules,
    startBonus,
    bonusPeriod,
    initialSharesPerToken,
    globalStartTime,
    owner,
    founderPercentage
  );

  await ampl.transfer(anotherAccount, $AMPL(50000));
  await ampl.approve(dist.address, $AMPL(50000), { from: anotherAccount });
  await ampl.approve(dist.address, $AMPL(50000), { from: owner });

  return {
    owner,
    anotherAccount,
    ampl,
    dist,
    founderPercentage,
    userPercentage,
  };
}

module.exports = {
  setupContractsAndAccounts,
  defaultParams,
  timeBonusParams,
  founderRewardsParams,
  badgerParams,
};
