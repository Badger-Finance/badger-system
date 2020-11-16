from tests.helpers import get_token_balances
import pytest
from brownie import *
from tests.badger_timelock.fixtures import timelock_unit


@pytest.fixture(scope="function", autouse="True")
def setup(timelock_unit):
    smartTimelock = timelock_unit.smartTimelock, stakingMock = (
        timelock_unit.stakingMock,
        governor,
    ) = timelock_unit.governor
    # Approve staking contract via governor
    smartTimelock.approveTransfer(stakingMock)
    # Approve staking pool to approve timelock tokens
    smartTimelock.call(
        timelock_unit.gToken,
        0,
        stakingMock.approve.encode_input(stakingMock, Wei("1000000000 ether")),
    )

    return timelock_unit


def test_stake_approved_contract(setup):
    ethGifter = setup.ethGifter
    deployer = setup.deployer
    smartTimelock = setup.smartTimelock
    team = setup.team


def test_transfer_and_retreive_approved_contract(setup):
    ethGifter = setup.ethGifter
    deployer = setup.deployer
    smartTimelock = setup.smartTimelock
    team = setup.team
    params = setup.params

    stakingAmount = Wei("10 ether")

    # Send tokens to staking pool
    preBalances = get_token_balances([smartTimelock, stakingMock], [gToken, stakingMock])

    smartTimelock.call(stakingMock, 0, stakingMock.stake.enocde_input(stakingAmount))

    postBalances = get_token_balances([smartTimelock, stakingMock], [gToken, stakingMock])

    assert postBalances.smartTimelock.gToken == preBalances.smartTimelock.gToken - stakingAmount
    assert postBalances.stakingMock.gToken == preBalances.stakingMock.gToken + stakingAmount

    smartTimelock.call(stakingMock, 0, stakingMock.stake.enocde_input(stakingAmount))

    #   it("Should be able to transfer & retrieve locked tokens to contract with active approval", async function() {
    #     // Send tokens to staking pool
    #     preBalances=getTokenBalances(
    #       provider,
    #       [gToken.address, stakingMock.address],
    #       [smartTimelock.address, stakingMock.address]
    #     )

    #     (
    #       smartTimelock
    #         .connect(team[0])
    #         .call(
    #           stakingMock.address,
    #           0,
    #           iStakingMock.encodeFunctionData("stake", [stakingAmount])
    #         )
    #     ).wait()

    #     postStakeBalances=getTokenBalances(
    #       provider,
    #       [gToken.address, stakingMock.address],
    #       [smartTimelock.address, stakingMock.address]
    #     )

    #     assert
    #       postStakeBalances[smartTimelock.address][gToken.address].toString(),
    #       "Expect timelock to lose stakingAmount of locked tokens"=
    #       preBalances[smartTimelock.address][gToken.address]
    #         .sub(stakingAmount)
    #         .toString()
    #     )
    #     assert
    #       postStakeBalances[stakingMock.address][gToken.address],
    #       "Expect staking contract to gain stakingAmount of locked tokens"=stakingAmount)

    #     (
    #       smartTimelock
    #         .connect(team[0])
    #         .call(
    #           stakingMock.address,
    #           0,
    #           iStakingMock.encodeFunctionData("unstake", [stakingAmount])
    #         )
    #     ).wait()

    #     postUnstakeBalances=getTokenBalances(
    #       provider,
    #       [gToken.address, stakingMock.address],
    #       [smartTimelock.address, stakingMock.address]
    #     )

    #     assert
    #       postUnstakeBalances[smartTimelock.address][gToken.address],
    #       "Expect timelock to gain stakingAmount of locked tokens"=
    #       postStakeBalances[smartTimelock.address][gToken.address].add(
    #         stakingAmount
    #       )
    #     )

    #     assert
    #       postUnstakeBalances[smartTimelock.address][gToken.address].toString(),
    #       "Expect timelock to gain stakingAmount of distributed tokens"=
    #       preBalances[smartTimelock.address][gToken.address].toString()
    #     )
    #     assert
    #       postUnstakeBalances[stakingMock.address][gToken.address],
    #       "Expect staking contract to lose stakingAmount of locked tokens"=0)
    #   })

    #   it("Should not be able to transfer locked tokens to contract with approval revoked", async function() {
    #     // Revoke contract on governor
    #     (
    #       smartTimelock
    #         .connect(governor)
    #         .revokeTransfer(stakingMock.address)
    #     ).wait()

    #     assert
    #       smartTimelock
    #         .connect(team[0])
    #         .call(
    #           stakingMock.address,
    #           0,
    #           iStakingMock.encodeFunctionData("stake", [stakingAmount])
    #         )
    #     ).to.be.reverted
    #   })

    #   it("Should not be able to retrieve staked tokens on revoked contract", async function() {
    #     (
    #       smartTimelock
    #         .connect(team[0])
    #         .call(
    #           stakingMock.address,
    #           0,
    #           iStakingMock.encodeFunctionData("stake", [stakingAmount])
    #         )
    #     ).wait()

    #     // Revoke contract on governor
    #     (
    #       smartTimelock
    #         .connect(governor)
    #         .revokeTransfer(stakingMock.address)
    #     ).wait()

    #     (
    #       smartTimelock
    #         .connect(team[0])
    #         .call(
    #           stakingMock.address,
    #           0,
    #           iStakingMock.encodeFunctionData("unstake", [stakingAmount])
    #         )
    #     ).wait()
    #   })
