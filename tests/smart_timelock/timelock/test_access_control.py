import pytest
from brownie import *
import brownie
from helpers.constants import *
from tests.smart_timelock.fixtures import timelock_unit

@pytest.fixture(scope="module", autouse="True")
def setup(timelock_unit):
    yield timelock_unit


def test_check_initial_params():
  """
  Initial parameters should match deploy parameters
  """
  token = setup.smartTimelock.token()
  beneficiary = setup.smartTimelock.beneficiary()
  release = setup.smartTimelock.releaseTime()

  assert token == setup.gToken
  assert beneficiary == setup.team[0]
  assert release == setup.unlockTime


def test_release_funds_before_allowed():
  with brownie.reverts():
    setup.gToken.transfer(setup.smartTimelock, setup.params.releaseAmount, {
                          'from': setup.deployer})


def test_release_funds_after_expiration():
  gToken = setup.gToken
  smartTimelock = setup.smartTimelock
  team = setup.team
  tokenGifter = setup.tokenGifter
  params = setup.params

  releaseAmount = setup.params.transferAmount
  gToken.transfer(smartTimelock, releaseAmount)
  smartTimelock.release()

  beneficiaryPostBalance = gToken.balanceOf(team[0])
  timelockPostBalance = gToken.balanceOf(smartTimelock)

  assert beneficiaryPostBalance == releaseAmount
  assert timelockPostBalance == 0

  preBalance = gToken.balanceOf(smartTimelock)

  smartTimelock.call(tokenGifter, 0, tokenGifter.requestTransfer.encode_input(
      gToken, params.tokenRequestAmount))

  postBalance = gToken.balanceOf(smartTimelock)

  assert preBalance + params.tokenRequestAmount == postBalance

def test_invalid_transfer_lock_token():
  """
  Should not be able to transfer locked tokens using call function
  """
  gToken = setup.gToken
  smartTimelock = setup.smartTimelock
  team = setup.team
  tokenGifter = setup.tokenGifter
  stakingMock = setup.stakingMock
  params = setup.params
  governor = setup.governor
  miscToken = setup.miscToken
  tokenGifterAmount = setup.tokenGifterAmount

  transferAction = miscToken.transfer.encode_input(team[0], tokenGifterAmount)

  with brownie.reverts():
    smartTimelock.call(gToken, 0, transferAction, {'from': team[0]})

  preBalance=miscToken.balanceOf(smartTimelock)
  smartTimelock.call(miscToken, 0, transferAction, {'from': team[0]})
  postBalance=miscToken.balanceOf(smartTimelock)
  assert postBalance == preBalance - tokenGifterAmount

  with brownie.reverts("smart-timelock/no-locked-token-claim"):
    smartTimelock.claimToken(gToken, {'from': team[0]})

  smartTimelock.claimToken(miscToken, {'from': team[0]})
  postBalance=miscToken.balanceOf(smartTimelock.address)
  assert postBalance == 0

  stakingAmount = Wei("100 ether")
  approveAction = miscToken.approve.encode_input(stakingMock, MaxUint256)
  stakeAction = stakingMock.stake.encode_input(stakingAmount)

  smartTimelock.call(gToken, 0, approveAction, {'from': team[0]})

  with brownie.reverts():
    smartTimelock.call(stakingMock, 0, stakeAction)

  # Governor should be able to approve contracts
  smartTimelock.approveTransfer(stakingMock, {'from': governor})

  # Governor should be able to revoke approved contracts
  tx = smartTimelock.revokeTransfer(stakingMock, {'from': governor})
  assert len(tx.events["RevokeTransfer"]) > 0
  assert tx.events["RevokeTransfer"][0].to == stakingMock

  # Non-Governor should not be able to approve contracts
  with brownie.reverts("smart-timelock/only-governor"):
    smartTimelock.approveTransfer(stakingMock, {'from': team[0]})

  # Non-Governor should not be able to revoke approved contracts
  with brownie.reverts("smart-timelock/only-governor"):
    smartTimelock.revokeTransfer(stakingMock, {'from': team[0]})

  # Staking on approved contract
  stakingAmount = Wei("100 ether")
  smartTimelock.approveTransfer(stakingMock, {'from': governor })
  smartTimelock.call(gToken, 0, miscToken.approve.encode_input(stakingMock, MaxUint256), {'from': team[0]})

#         // Send tokens to staking pool
#         preBalances=getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartTimelock.address, stakingMock.address]
#         )

#         (
#           smartTimelock
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).wait()

#         postStakeBalances=getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartTimelock.address, stakingMock.address]
#         )

#         assert
#           postStakeBalances[smartTimelock.address][gToken.address].toString(),
#           "Expect timelock to lose stakingAmount of locked tokens"=
#           preBalances[smartTimelock.address][gToken.address]
#             .sub(stakingAmount)
#             .toString()
#         )
#         assert
#           postStakeBalances[stakingMock.address][gToken.address],
#           "Expect staking contract to gain stakingAmount of locked tokens"=stakingAmount)

#         (
#           smartTimelock
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("unstake", [stakingAmount])
#             )
#         ).wait()

#         postUnstakeBalances=getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartTimelock.address, stakingMock.address]
#         )

#         assert
#           postUnstakeBalances[smartTimelock.address][gToken.address],
#           "Expect timelock to gain stakingAmount of locked tokens"=
#           postStakeBalances[smartTimelock.address][gToken.address].add(
#             stakingAmount
#           )
#         )

#         assert
#           postUnstakeBalances[smartTimelock.address][gToken.address].toString(),
#           "Expect timelock to gain stakingAmount of distributed tokens"=
#           preBalances[smartTimelock.address][gToken.address].toString()
#         )
#         assert
#           postUnstakeBalances[stakingMock.address][gToken.address],
#           "Expect staking contract to lose stakingAmount of locked tokens"=0)
#       })

#       it("Should not be able to transfer locked tokens to contract with approval revoked", async function() {
#         // Revoke contract on governor
#         (
#           smartTimelock
#             .connect(governor)
#             .revokeTransfer(stakingMock.address)
#         ).wait()

#         assert
#           smartTimelock
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).to.be.reverted
#       })

#       it("Should not be able to retrieve staked tokens on revoked contract", async function() {
#         (
#           smartTimelock
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).wait()

#         // Revoke contract on governor
#         (
#           smartTimelock
#             .connect(governor)
#             .revokeTransfer(stakingMock.address)
#         ).wait()

#         (
#           smartTimelock
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("unstake", [stakingAmount])
#             )
#         ).wait()
#       })
#     })
#   })

#   it("Non-beneficiary should not be able to call owner-gated functions", async function() {
#     requestTransferAction=iTokenGifter.encodeFunctionData(
#       "requestTransfer",
#       [gToken.address, tokenRequestAmount]
#     )

#     assert
#       smartTimelock
#         .connect(minnow)
#         .call(tokenGifter.address, 0, requestTransferAction)
#     ).to.be.reverted

#     assert smartTimelock.connect(minnow).claimToken(gToken.address)).to.be
#       .reverted

#     assert smartTimelock.connect(minnow).claimToken(miscToken.address)).to
#       .be.reverted

#     assert smartTimelock.connect(minnow).claimEther()).to.be.reverted
#   })
# })
