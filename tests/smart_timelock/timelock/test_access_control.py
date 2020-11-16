# import pytest
# from brownie import *
# import brownie


# @pytest.fixture(scope="module", autouse="True")
# def setup(timelock_unit):
#     yield timelock_unit


# def check_initial_params_test():
#   """
#   Initial parameters should match deploy parameters
#   """
#   token = setup.smartTimelock.token()
#   beneficiary = setup.smartTimelock.beneficiary()
#   release = setup.smartTimelock.releaseTime()

#   assert token == setup.gToken
#   assert beneficiary == setup.team[0]
#   assert release == setup.unlockTime


# def release_funds_before_allowed_test():
#   with brownie.reverts():
#     setup.gToken.transfer(setup.smartTimelock, setup.params.releaseAmount, {
#                           'from': setup.deployer})


# def release_funds_after_expiration_test():
#   gToken = setup.gToken
#   smartTimelock = setup.smartTimelock
#   team = setup.team
#   tokenGifter = setup.tokenGifter
#   params = setup.params

#   releaseAmount = setup.params.transferAmount
#   gToken.transfer(smartTimelock, releaseAmount)
#   smartTimelock.release()

#   beneficiaryPostBalance = gToken.balanceOf(team[0])
#   timelockPostBalance = gToken.balanceOf(smartTimelock)

#   assert beneficiaryPostBalance == releaseAmount
#   assert timelockPostBalance == 0

#   preBalance = gToken.balanceOf(smartTimelock)

#   smartTimelock.call(tokenGifter, 0, tokenGifter.requestTransfer.encode_input(
#       gToken, params.tokenRequestAmount))

#   postBalance = gToken.balanceOf(smartTimelock)

#   assert preBalance + params.tokenRequestAmount == postBalance

# def test_invalid_transfer_lock_token():
#   """
#   Should not be able to transfer locked tokens using call function
#   """

#   transferAction = mockToken.transfer.encode_input(team[0], tokenGifterAmount)

#   with brownie.reverts():

#   assert smartTimelock.connect(team[0]).call(gToken.address, 0, transferAction)
#   ).to.be.revertedWith("smart-timelock/locked-balance-check")
# })

#     it("Should be able to transfer other tokens using call function", async function() {
#       transferAction=iERC20.encodeFunctionData("transfer", [
#         team[0],
#         tokenGifterAmount,
#       ])

#       preBalance=miscToken.balanceOf(smartTimelock.address)

#       (
#         smartTimelock
#           .connect(team[0])
#           .call(miscToken.address, 0, transferAction)
#       ).wait()

#       postBalance=miscToken.balanceOf(smartTimelock.address)

#       assert postBalance=preBalance.sub(tokenGifterAmount))
#     })

#     it("Should not be able to claim locked tokens using claimToken()", async function() {
#       assert
#         smartTimelock.connect(team[0]).claimToken(gToken.address)
#       ).to.be.revertedWith("smart-timelock/no-locked-token-claim")
#     })

#     it("Should be able to claim other tokens using claimToken()", async function() {
#       (
#         smartTimelock.connect(team[0]).claimToken(miscToken.address)
#       ).wait()

#       postBalance=miscToken.balanceOf(smartTimelock.address)
#       assert postBalance=0)
#     })

#     it("Should not be able to transfer locked tokens to contract without approval", async function() {
#       (
#         smartTimelock
#           .connect(team[0])
#           .call(
#             gToken.address,
#             0,
#             iERC20.encodeFunctionData("approve", [
#               stakingMock.address,
#               ethers.constants.MaxUint256,
#             ])
#           )
#       ).wait()
#       let stakingAmount=utils.parseEther("100")
#       assert
#         smartTimelock
#           .connect(team[0])
#           .call(
#             stakingMock.address,
#             0,
#             iStakingMock.encodeFunctionData("stake", [stakingAmount])
#           )
#       ).to.be.reverted
#     })

#     it("Governor should be able to approve contracts", async function() {
#       (
#         smartTimelock
#           .connect(governor)
#           .approveTransfer(stakingMock.address)
#       ).wait()

#       // Check event emission
#       approveEvent=smartTimelock.queryFilter(
#         smartTimelock.filters.ApproveTransfer(),
#         "latest"
#       )

#       assert approveEvent[0].args?.to=stakingMock.address)
#     })

#     it("Governor should be able to revoke approved contracts", async function() {
#       (
#         smartTimelock
#           .connect(governor)
#           .approveTransfer(stakingMock.address)
#       ).wait()

#       (
#         smartTimelock
#           .connect(governor)
#           .revokeTransfer(stakingMock.address)
#       ).wait()

#       // Check event emission
#       revokeEvent=smartTimelock.queryFilter(
#         smartTimelock.filters.RevokeTransfer(),
#         "latest"
#       )

#       assert revokeEvent[0].args?.to=stakingMock.address)
#     })

#     it("Non-Governor should not be able to approve contracts", async function() {
#       assert
#         smartTimelock.connect(team[0]).approveTransfer(stakingMock.address)
#       ).to.been.revertedWith("smart-timelock/only-governor")
#     })

#     it("Non-Governor should not be able to revoke approved contracts", async function() {
#       assert
#         smartTimelock.connect(team[0]).revokeTransfer(stakingMock.address)
#       ).to.been.revertedWith("smart-timelock/only-governor")
#     })

#     describe("Staking on approved contract", function() {
#       let stakingAmount=utils.parseEther("100")
#       beforeEach(async function() {
#         // Approve contract on governor
#         (
#           smartTimelock
#             .connect(governor)
#             .approveTransfer(stakingMock.address)
#         ).wait()
#         // Approve staking pool to spend tokens
#         (
#           smartTimelock
#             .connect(team[0])
#             .call(
#               gToken.address,
#               0,
#               iERC20.encodeFunctionData("approve", [
#                 stakingMock.address,
#                 ethers.constants.MaxUint256,
#               ])
#             )
#         ).wait()
#       })

#       it("Should be able to transfer & retrieve locked tokens to contract with active approval", async function() {
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
