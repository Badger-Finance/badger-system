describe("when totalLocked>0, rebase increases supply", function() {
      timeController = new TimeController()
      beforeEach(async function() {
        this.timeout(0)
        ampl.approve(geyser.address, AMPL(150))
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        timeController.initialize()
        checkAmplAprox(geyser.totalLocked.call(), 100)
        invokeRebase(ampl, 100)
      })
      it("should updated the locked pool balance", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        checkAmplAprox(geyser.totalLocked.call(), 50 + 200 * 0.9)
      })
      it("should updated the locked pool balance", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)

        checkAmplAprox(geyser.totalLocked.call(), 50 + 200 * 0.9)
      })
      it("should log TokensUnlocked and TokensLocked", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        r = lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)

        let l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
        checkAmplAprox(l.args.amount, 200 * 0.1)
        checkAmplAprox(l.args.total, 200 * 0.9)

        l = r.logs.filter((l) => l.event === "TokensLocked")[0]
        checkAmplAprox(l.args.amount, 50)
        checkAmplAprox(l.args.total, 50.0 + 200.0 * 0.9)
        expect(l.args.durationSec).to.be.bignumber.equal(`${ONE_YEAR}`)
      })
      it("should create a schedule", async function() {
        timeController.advanceTime(ONE_YEAR / 10)
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        s = geyser.unlockSchedules.call(1)
        checkSharesAprox(
          s[0],
          AMPL(25).mul(new BN(expectedParams.initialSharesPerToken))
        )
        checkSharesAprox(s[1], new BN(0))
        expect(s[2].add(s[4])).to.be.bignumber.equal(s[3])
        expect(s[4]).to.be.bignumber.equal(`${ONE_YEAR}`)
        expect(geyser.unlockScheduleCount.call()).to.be.bignumber.equal(
          "2"
        )
      })
    })

    describe("when totalLocked>0, rebase decreases supply", function() {
      let currentTime
      beforeEach(async function() {
        this.timeout(0)
        ampl.approve(geyser.address, AMPL(150))
        lockTokensAtLatestTime(geyser, AMPL(100), ONE_YEAR)

        currentTime = time.latest()
        checkAmplAprox(geyser.totalLocked.call(), 100)
        invokeRebase(ampl, -50)
      })
      it("should updated the locked pool balance", async function() {
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        checkAmplAprox(geyser.totalLocked.call(), 100)
      })
      it("should log TokensUnlocked and TokensLocked", async function() {
        currentTime = currentTime.add(new BN(ONE_YEAR / 10))
        setTimeForNextTransaction(currentTime)
        r = lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)

        let l = r.logs.filter((l) => l.event === "TokensUnlocked")[0]
        checkAmplAprox(l.args.amount, 50 * 0.1)
        checkAmplAprox(l.args.total, 50 * 0.9)

        l = r.logs.filter((l) => l.event === "TokensLocked")[0]
        checkAmplAprox(l.args.amount, 50)
        checkAmplAprox(l.args.total, 50 * 0.9 + 50)
        expect(l.args.durationSec).to.be.bignumber.equal(`${ONE_YEAR}`)
      })
      it("should create a schedule", async function() {
        lockTokensAtLatestTime(geyser, AMPL(50), ONE_YEAR)
        s = geyser.unlockSchedules.call(1)

        checkSharesAprox(
          s[0],
          AMPL(100).mul(new BN(expectedParams.initialSharesPerToken))
        )
        expect(s[1]).to.be.bignumber.equal(AMPL(0))
        expect(s[2].add(s[4])).to.be.bignumber.equal(s[3])
        expect(s[4]).to.be.bignumber.equal(`${ONE_YEAR}`)
        expect(geyser.unlockScheduleCount.call()).to.be.bignumber.equal(
          "2"
        )
      })
    })
  })