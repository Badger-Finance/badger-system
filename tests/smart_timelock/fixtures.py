import pytest
from brownie import *
from dotmap import DotMap


@pytest.fixture(scope="module")
def timelock_unit():
    unlockTime = chain.time() + 1000000
    deployer = accounts[0]
    team = [accounts[1], accounts[2], accounts[3]]
    governor = accounts[5]
    minnow = accounts[4]

    tokenGifterAmount = Wei("500 ether")
    tokenRequestAmount = Wei("100 ether")
    transferAmount = Wei("500000 ether")

    tokenGifter = TokenGifter.deploy({"from": deployer})
    ethGifter = EthGifter.deploy({"from": deployer})

    gToken = MockToken.deploy({"from": deployer})
    gToken.initialize(
        [
            web3.toChecksumAddress(tokenGifter.address),
            web3.toChecksumAddress(deployer.address),
        ],
        [tokenGifterAmount * 2, transferAmount * 10],
        {"from": deployer},
    )

    smartVesting = SmartVesting.deploy({"from": deployer})
    smartVesting.initialize(gToken, team[0], governor, unlockTime, {"from": deployer})

    gToken.transfer(smartVesting, transferAmount)

    stakingMock = StakingMock.deploy({"from": deployer})
    stakingMock.initialize(gToken, {"from": deployer})

    deployer.transfer(ethGifter, Wei("10 ether"))

    miscToken = MockToken.deploy({"from": deployer})
    miscToken.initialize(
        [
            web3.toChecksumAddress(tokenGifter.address),
            web3.toChecksumAddress(smartVesting.address),
        ],
        [tokenGifterAmount * 2, tokenGifterAmount],
        {"from": deployer},
    )

    yield DotMap(
        tokenGifter=tokenGifter,
        ethGifter=ethGifter,
        smartVesting=smartVesting,
        stakingMock=stakingMock,
        miscToken=miscToken,
        deployer=deployer,
        team=team,
        governor=governor,
        minnow=minnow,
        params={
            "tokenGifterAmount": tokenGifterAmount,
            "tokenRequestAmount": tokenRequestAmount,
            "transferAmount": transferAmount,
            "unlockTime": unlockTime,
        },
    )


@pytest.fixture(scope="module")
def vesting_unit():
    start = chain.time + 1000
    cliffDuration = days(30)
    duration = days(335)
    deployer = accounts[0]
    team = [accounts[1], accounts[2], accounts[3]]
    governor = accounts[5]
    minnow = accounts[4]

    tokenGifterAmount = Wei("500 ether")
    tokenRequestAmount = Wei("100 ether")
    transferAmount = Wei("500000 ether")

    tokenGifter = TokenGifter.deploy({"from": deployer})
    ethGifter = EthGifter.deploy({"from": deployer})

    gToken = MockToken.deploy({"from": deployer})
    gToken.initialize(
        [
            web3.toChecksumAddress(tokenGifter.address),
            web3.toChecksumAddress(deployer.address),
        ],
        [tokenGifterAmount * 2, transferAmount * 10],
        {"from": deployer},
    )

    smartVesting = SmartVesting.deploy({"from": deployer})
    smartVesting.initialize(
        gToken, team[0], governor, start, cliffDuration, duration, {"from": deployer}
    )

    gToken.transfer(smartVesting, transferAmount)

    stakingMock = StakingMock.deploy({"from": deployer})
    stakingMock.initialize(gToken, {"from": deployer})

    deployer.transfer(ethGifter, Wei("10 ether"))

    miscToken = MockToken.deploy({"from": deployer})
    miscToken.initialize(
        [
            web3.toChecksumAddress(tokenGifter.address),
            web3.toChecksumAddress(smartVesting.address),
        ],
        [tokenGifterAmount * 2, tokenGifterAmount],
        {"from": deployer},
    )

    yield DotMap(
        tokenGifter=tokenGifter,
        ethGifter=ethGifter,
        smartVesting=smartVesting,
        stakingMock=stakingMock,
        miscToken=miscToken,
        deployer=deployer,
        team=team,
        governor=governor,
        minnow=minnow,
        params={
            "tokenGifterAmount": tokenGifterAmount,
            "tokenRequestAmount": tokenRequestAmount,
            "transferAmount": transferAmount,
            "start": start,
            "cliffDuration": cliffDuration,
            "duration": duration,
        },
    )
