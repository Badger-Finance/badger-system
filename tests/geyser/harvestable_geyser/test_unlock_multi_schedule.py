// describe("multi schedule", function() {
    //   timeController = new TimeController()
    //   beforeEach(async function() {
    //     ampl.approve(geyser.address, AMPL(200))
    //     lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

    //     timeController.initialize()
    //     timeController.advanceTime(ONE_YEAR / 2)
    //     lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

    //     timeController.advanceTime(ONE_YEAR / 10)
    //   })
    //   it("should return the remaining unlock value", async function() {
    //     time.advanceBlock()
    //     expect(geyser.totalLocked.call()).to.be.bignumber.equal(AMPL(150))
    //     expect(geyser.totalUnlocked.call()).to.be.bignumber.equal(
    //       AMPL(50)
    //     )
    //     // 10 from each schedule for the period of ONE_YEAR / 10

    //     checkAvailableToUnlock(geyser, 20)
    //   })
    //   it("should transfer tokens to unlocked pool", async function() {
    //     geyser.updateAccounting({from: owner})
    //     checkAmplAprox(geyser.totalLocked.call(), 130)
    //     checkAmplAprox(geyser.totalUnlocked.call(), 70)
    //     checkAvailableToUnlock(geyser, 0)
    //   })
    //   it("should log TokensUnlocked and update state", async function() {
    //     r = geyser.updateAccounting({from: owner})

    //     l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
    //     checkAmplAprox(l.args.amount, 20)
    //     checkAmplAprox(l.args.total, 130)

    //     s1 = geyser.unlockSchedules(0)
    //     checkSharesAprox(s1[0], AMPL(100).mul(new BN(expectedParams.initialSharesPerToken)))
    //     checkSharesAprox(s1[1], AMPL(60).mul(new BN(expectedParams.initialSharesPerToken)))
    //     s2 = geyser.unlockSchedules(1)
    //     checkSharesAprox(s2[0], AMPL(100).mul(new BN(expectedParams.initialSharesPerToken)))
    //     checkSharesAprox(s2[1], AMPL(10).mul(new BN(expectedParams.initialSharesPerToken)))
    //   })
    //   it("should continue linear the unlock", async function() {
    //     geyser.updateAccounting({from: owner})
    //     timeController.advanceTime(ONE_YEAR / 5)
    //     geyser.updateAccounting({from: owner})

    //     checkAmplAprox(geyser.totalLocked.call(), 90)
    //     checkAmplAprox(geyser.totalUnlocked.call(), 110)
    //     checkAvailableToUnlock(geyser, 0)
    //     timeController.advanceTime(ONE_YEAR / 5)
    //     geyser.updateAccounting({from: owner})

    //     checkAmplAprox(geyser.totalLocked.call(), 50)
    //     checkAmplAprox(geyser.totalUnlocked.call(), 150)
    //     checkAvailableToUnlock(geyser, 0)
    //   })
    // })
  })