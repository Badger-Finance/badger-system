import pytest
from brownie import * 
import brownie
from dotmap import DotMap
from tests.badger_geyser.geyser_helpers import *
from tests.badger_geyser.geyser_fixtures import *
from utils.time_utils import *
import time

def checkAvailableToUnlock(geyser, v):
  u = geyser.totalUnlocked.call()
  r = geyser.updateAccounting.call()
  // console.log('Total unlocked: ', u.toString(), 'total unlocked after: ', r[1].toString())
  checkAmplAprox(r[1].sub(u), v)

def setup():
    yield setupContractsAndAccounts(defaultParams)

def test_params(setup):
    geyser = setup.geyser
    ampl = setup.ampl
    assert geyser.getDistributionToken() == ampl

def test_lock_tokens_not_approved(setup):
    ampl = setup.ampl
    owner = setup.owner
    expectedParams = setup.expectedParams

    d = BadgerGeyser.new(
        ampl.address,
        ampl.address,
        1,
        expectedParams.startBonus,
        expectedParams.bonusPeriod,
        expectedParams.initialSharesPerToken,
        0,
        owner,
        0
    )

    with brownie.reverts():
        d.lockTokens(AMPL(10), ONE_YEAR, now())

def test_exceed_max_unlock_schedules():
    geyser = BadgerGeyser.new(
        ampl.address,
        ampl.address,
        1,
        expectedParams.startBonus,
        expectedParams.bonusPeriod,
        expectedParams.initialSharesPerToken,
        0,
        owner,
        0
    )
    ampl.approve(geyser, AMPL(100))
    lockTokensAtLatestTime(geyser, AMPL(10), ONE_YEAR)

    with brownie.reverts():
        geyser.lockTokens(AMPL(10), ONE_YEAR, now()),
        "BadgerGeyser: reached maximum unlock schedules"


  describe("unlockTokens", function() {
    describe("single schedule", function() {
      describe("after waiting for 1/2 the duration", function() {
        timeController = new TimeController()
        beforeEach(async function() {
          this.timeout(0)
          ampl.approve(geyser.address, AMPL(100))
          lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

          timeController.initialize()
          timeController.advanceTime(ONE_YEAR / 2)
        })

        describe("when supply is unchanged", function() {
          it("should unlock 1/2 the tokens", async function() {
            timeController.executeEmptyBlock()
            expect(geyser.totalLocked.call()).to.be.bignumber.equal(
              AMPL(100)
            )
            expect(geyser.totalUnlocked.call()).to.be.bignumber.equal(
              AMPL(0)
            )
            checkAvailableToUnlock(geyser, 50)
          })
          it("should transfer tokens to unlocked pool", async function() {
            geyser.updateAccounting({ from: owner })
            checkAmplAprox(geyser.totalLocked.call(), 50)
            checkAmplAprox(geyser.totalUnlocked.call(), 50)
            checkAvailableToUnlock(geyser, 0)
          })
          it("should log TokensUnlocked and update state", async function() {
            r = geyser.updateAccounting({ from: owner })
            l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
            checkAmplAprox(l.args.amount, 50)
            checkAmplAprox(l.args.total, 50)
            s = geyser.unlockSchedules(0)
            expect(s[0]).to.be.bignumber.equal(
              AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
            )
            checkSharesAprox(
              s[1],
              AMPL(50).mul(new BN(expectedParams.initialSharesPerToken))
            )
          })
        })

        describe("when rebase increases supply", function() {
          beforeEach(async function() {
            this.timeout(0)
            invokeRebase(ampl, 100)
          })
          it("should unlock 1/2 the tokens", async function() {
            timeController.executeEmptyBlock()
            expect(geyser.totalLocked.call()).to.be.bignumber.equal(
              AMPL(200)
            )
            expect(geyser.totalUnlocked.call()).to.be.bignumber.equal(
              AMPL(0)
            )
            checkAvailableToUnlock(geyser, 100)
          })
          it("should transfer tokens to unlocked pool", async function() {
            // printStatus(geyser)
            geyser.updateAccounting({ from: owner })

            checkAmplAprox(geyser.totalLocked.call(), 100)
            checkAmplAprox(geyser.totalUnlocked.call(), 100)
            checkAvailableToUnlock(geyser, 0)
          })
        })

        describe("when rebase decreases supply", function() {
          beforeEach(async function() {
            this.timeout(0)
            invokeRebase(ampl, -50)
          })
          it("should unlock 1/2 the tokens", async function() {
            expect(geyser.totalLocked.call()).to.be.bignumber.equal(
              AMPL(50)
            )
            checkAvailableToUnlock(geyser, 25)
          })
          it("should transfer tokens to unlocked pool", async function() {
            expect(geyser.totalLocked.call()).to.be.bignumber.equal(
              AMPL(50)
            )
            expect(geyser.totalUnlocked.call()).to.be.bignumber.equal(
              AMPL(0)
            )
            geyser.updateAccounting({ from: owner })

            checkAmplAprox(geyser.totalLocked.call(), 25)
            checkAmplAprox(geyser.totalUnlocked.call(), 25)
            checkAvailableToUnlock(geyser, 0)
          })
        })
      })

      describe("after waiting > the duration", function() {
        beforeEach(async function() {
          this.timeout(0)
          ampl.approve(geyser.address, AMPL(100))
          lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

          time.increase(2 * ONE_YEAR)
        })
        it("should unlock all the tokens", async function() {
          checkAvailableToUnlock(geyser, 100)
        })
        it("should transfer tokens to unlocked pool", async function() {
          expect(geyser.totalLocked.call()).to.be.bignumber.equal(
            AMPL(100)
          )
          expect(geyser.totalUnlocked.call()).to.be.bignumber.equal(
            AMPL(0)
          )
          geyser.updateAccounting({ from: owner })
          expect(geyser.totalLocked.call()).to.be.bignumber.equal(AMPL(0))
          checkAmplAprox(geyser.totalUnlocked.call(), 100)
          checkAvailableToUnlock(geyser, 0)
        })
        it("should log TokensUnlocked and update state", async function() {
          r = geyser.updateAccounting({ from: owner })
          l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
          checkAmplAprox(l.args.amount, 100)
          checkAmplAprox(l.args.total, 0)
          s = geyser.unlockSchedules(0)
          expect(s[0]).to.be.bignumber.equal(
            AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
          )
          expect(s[1]).to.be.bignumber.equal(
            AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
          )
        })
      })

      describe("dust tokens due to division underflow", function() {
        beforeEach(async function() {
          this.timeout(0)
          ampl.approve(geyser.address, AMPL(100))
          lockTokensAtLatestTime(geyser, AMPL(1), 10 * ONE_YEAR)
        })
        it("should unlock all tokens", async function() {
          // 1 AMPL locked for 10 years. Almost all time passes upto the last minute.
          // 0.999999809 AMPLs are unlocked.
          // 1 minute passes, Now: all of the rest are unlocked: 191
          // before (#24): only 190 would have been unlocked and 0.000000001 AMPL would be
          // locked.
          time.increase(10 * ONE_YEAR - 60)
          r1 = geyser.updateAccounting({ from: owner })
          l1 = r1.logs.filter((l) => l.event === "TokensUnlocked")[0]
          time.increase(65)
          r2 = geyser.updateAccounting({ from: owner })
          l2 = r2.logs.filter((l) => l.event === "TokensUnlocked")[0]
          expect(l1.args.amount.add(l2.args.amount)).to.be.bignumber.equal(
            AMPL(1)
          )
        })
      })
    })

    

  describe("updateAccounting", function() {
    let _r, _t
    beforeEach(async function() {
      this.timeout(0)
      _r = geyser.updateAccounting.call({ from: owner })
      _t = time.latest()
      ampl.approve(geyser.address, AMPL(300))
      geyser.stake(AMPL(100), [])
      lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

      time.increase(ONE_YEAR / 2)
      lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

      time.increase(ONE_YEAR / 10)
    })

    describe("when user history does exist", async function() {
      it("should return the system state", async function() {
        r = geyser.updateAccounting.call({ from: owner })
        t = time.latest()
        checkAmplAprox(r[0], 130)
        checkAmplAprox(r[1], 70)
        timeElapsed = t.sub(_t)
        expect(
          r[2].div(
            new BN(100e9).mul(new BN(expectedParams.initialSharesPerToken))
          ),
          "totalUnlocked"
        )
          .to.be.bignumber.above(timeElapsed.sub(new BN(5)))
          .and.bignumber.below(timeElapsed.add(new BN(5)))
        expect(
          r[3].div(
            new BN(100e9).mul(new BN(expectedParams.initialSharesPerToken))
          ),
          "totals.stakingShareSeconds"
        )
          .to.be.bignumber.above(timeElapsed.sub(new BN(5)))
          .and.bignumber.below(timeElapsed.add(new BN(5)))
        checkAmplAprox(r[4], 70)
        checkAmplAprox(r[4], 70)
        delta = new BN(r[5]).sub(new BN(_r[5]))
        expect(delta, "delta")
          .to.be.bignumber.above(timeElapsed.sub(new BN(1)))
          .and.bignumber.below(timeElapsed.add(new BN(1)))
      })
    })

    describe("when user history does not exist", async function() {
      it("should return the system state", async function() {
        r = geyser.updateAccounting.call({
          from: constants.ZERO_ADDRESS,
        })
        t = time.latest()
        checkAmplAprox(r[0], 130)
        checkAmplAprox(r[1], 70)
        timeElapsed = t.sub(_t)
        expect(
          r[2].div(
            new BN(100e9).mul(new BN(expectedParams.initialSharesPerToken))
          ),
          "totals.stakingShareSeconds"
        ).to.be.bignumber.equal("0")
        expect(
          r[3].div(
            new BN(100e9).mul(new BN(expectedParams.initialSharesPerToken))
          ),
          "_totalStakingShareSeconds"
        )
          .to.be.bignumber.above(timeElapsed.sub(new BN(5)))
          .and.bignumber.below(timeElapsed.add(new BN(5)))
        checkAmplAprox(r[4], 0)
        delta = new BN(r[5]).sub(new BN(_r[5]))
        expect(delta, "delta")
          .to.be.bignumber.above(timeElapsed.sub(new BN(1)))
          .and.bignumber.below(timeElapsed.add(new BN(1)))
      })
    })
  })
})
