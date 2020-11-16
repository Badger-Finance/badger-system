def

    describe("when totalLocked=0", function() {
      beforeEach(async function() {
        this.timeout(0)
        checkAmplAprox(geyser.totalLocked.call(), 0)
        ampl.approve(geyser.address, AMPL(100))
      })
      it("should updated the locked pool balance", async function() {
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        checkAmplAprox(geyser.totalLocked.call(), 100)
      })
      it("should create a schedule", async function() {
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        s = geyser.unlockSchedules.call(0)
        expect(s[0]).to.be.bignumber.equal(
          AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
        )
        expect(s[1]).to.be.bignumber.equal(AMPL(0))
        expect(s[2].add(s[4])).to.be.bignumber.equal(s[3])
        expect(s[4]).to.be.bignumber.equal(`${ONE_YEAR}`)
        expect(geyser.unlockScheduleCount.call()).to.be.bignumber.equal(
          "1"
        )
      })
      it("should log TokensLocked", async function() {
        r = lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        l = r.logs.filter((l) => l.event === "TokensLocked")[0]
        checkAmplAprox(l.args.amount, 100)
        checkAmplAprox(l.args.total, 100)
        expect(l.args.durationSec).to.be.bignumber.equal(`${ONE_YEAR}`)
      })
      it("should be protected", async function() {
        ampl.approve(geyser.address, AMPL(100))
       with brownie.reverts():
          geyser.lockTokens(AMPL(50), ONE_YEAR, now(), { from: anotherAccount }),
          "Ownable: caller is not the owner"
        )
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
      })
    })


    describe("when totalLocked=0", function() {
      beforeEach(async function() {
        this.timeout(0)
        checkAmplAprox(geyser.totalLocked.call(), 0)
        ampl.approve(geyser.address, AMPL(100))
      })
      it("should updated the locked pool balance", async function() {
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        checkAmplAprox(geyser.totalLocked.call(), 100)
      })
      it("should create a schedule", async function() {
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        s = geyser.unlockSchedules.call(0)
        expect(s[0]).to.be.bignumber.equal(
          AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
        )
        expect(s[1]).to.be.bignumber.equal(AMPL(0))
        expect(s[2].add(s[4])).to.be.bignumber.equal(s[3])
        expect(s[4]).to.be.bignumber.equal(`${ONE_YEAR}`)
        expect(geyser.unlockScheduleCount.call()).to.be.bignumber.equal(
          "1"
        )
      })
      it("should log TokensLocked", async function() {
        r = lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        l = r.logs.filter((l) => l.event === "TokensLocked")[0]
        checkAmplAprox(l.args.amount, 100)
        checkAmplAprox(l.args.total, 100)
        expect(l.args.durationSec).to.be.bignumber.equal(`${ONE_YEAR}`)
      })
      it("should be protected", async function() {
        ampl.approve(geyser.address, AMPL(100))
       with brownie.reverts():
          geyser.lockTokens(AMPL(50), ONE_YEAR, now(), { from: anotherAccount }),
          "Ownable: caller is not the owner"
        )
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
      })
    })

    
    describe("when totalLocked>0", function() {
      timeController = new TimeController()
      beforeEach(async function() {
        this.timeout(0)
        ampl.approve(geyser.address, AMPL(150))
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        timeController.initialize()
        checkAmplAprox(geyser.totalLocked.call(), 100)
      })
      it("should updated the locked and unlocked pool balance", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        checkAmplAprox(geyser.totalLocked.call(), 100 * 0.9 + 50)
      })
      it("should log TokensUnlocked and TokensLocked", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        r = lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)

        let l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
        checkAmplAprox(l.args.amount, 100 * 0.1)
        checkAmplAprox(l.args.total, 100 * 0.9)

        l = r.logs.filter((l) => l.event === "TokensLocked")[0]
        checkAmplAprox(l.args.amount, 50)
        checkAmplAprox(l.args.total, 100 * 0.9 + 50)
        expect(l.args.durationSec).to.be.bignumber.equal(`${ONE_YEAR}`)
      })
      it("should create a schedule", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        s = geyser.unlockSchedules.call(1)
        // struct UnlockSchedule {
        // 0   uint256 initialLockedShares
        // 1   uint256 unlockedShares
        // 2   uint256 lastUnlockTimestampSec
        // 3   uint256 endAtSec
        // 4   uint256 durationSec
        // }
        checkSharesAprox(
          s[0],
          AMPL(50).mul(new BN(expectedParams.initialSharesPerToken))
        )
        checkSharesAprox(s[1], new BN(0))
        expect(s[2].add(s[4])).to.be.bignumber.equal(s[3])
        expect(s[4]).to.be.bignumber.equal(`${ONE_YEAR}`)
        expect(geyser.unlockScheduleCount.call()).to.be.bignumber.equal(
          "2"
        )
      })
    })