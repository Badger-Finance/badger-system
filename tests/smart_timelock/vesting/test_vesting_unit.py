# import pytest
# from brownie import *
# import brownie
# from helpers.constants import *
# from tests.smart_timelock.fixtures import timelock_unit

# @pytest.fixture(scope="module")
# def setup(vesting_unit):
#     return vesting_unit

#     """
#     SETUp!!!!
#   describe("When SmartVesting has minority voting share", async function () {
#     beforeEach(async function () {
#       await await gToken.transfer(
#         smartVesting.address,
#         utils.parseEther("500000")
#       );
#     });

#     """
# @pytest.fixture(scope="module")
# def setup_with_tokens(vesting_unit):
#     deployer = vesting_unit.deployer
#     gToken = vesting_unit.gToken
#     smartVesting = vesting_unit.SmartVesting

#     vesting_unit.gToken.transfer(smartVesting, Wei("500000 ether"))

#     """
#     it("Should have correct parameters", async function () {
#         const token = await smartVesting.token();
#         const beneficiary = await smartVesting.beneficiary();
#         const cliff = await smartVesting.cliff();
#         const start = await smartVesting.start();
#         const duration = await smartVesting.duration();

#         expect(token, "token").to.be.equal(gToken.address);
#         expect(beneficiary, "beneficiary").to.be.equal(teamAddresses[0]);
#         expect(cliff, "cliff").to.equal(vestingParams.start); // Cliff tracks WHEN token releases begin, which is the start in our case
#         expect(start, "start").to.equal(vestingParams.start);
#         expect(duration, "duration").to.equal(vestingParams.duration);
#     });
#     """
# def test_correct_parameters(setup):
#     deployer = setup.deployer
#     gToken = setup.gToken
#     smartVesting = setup.SmartVesting
#     team = setup.team

#     assert smartVesting.token() == gToken
#     assert smartVesting.token() == team[0]
#     assert smartVesting.cliff() == setup.params.start + setup.params.cliff
#     assert smartVesting.start() == setup.params.start
#     assert smartVesting.duration() == setup.params.duration 

    
# def test_initial_release(setup):
#     deployer = setup.deployer
#     gToken = setup.gToken
#     smartVesting = setup.SmartVesting
#     team = setup.team
#     assert chain.time() < smartVesting.cliff()

#     with brownie.reverts():
#         smartVesting.release()

#     # Sleep until just before cliff ends
#     chain.sleep(smartVesting.cliff - chain.time() - 1)
#     chain.mine()

#     with brownie.reverts():
#         smartVesting.release()

#     chain.sleep(15)
#     chain.mine()

#     pre = gToken.balanceOf(smartVesting.recipient())
#     smartVesting.release()
#     post = gToken.balanceOf(smartVesting.recipient())

#     assert post > pre

#     """
#   it("Should be able to release appropriate funds before release time", async function () {
#     const releaseAmount = transferAmount;

#     await (
#       await gToken
#         .connect(deployer)
#         .transfer(smartVesting.address, releaseAmount)
#     ).wait();

#     const before = await getTokenBalances(provider, [gToken.address], [teamAddresses[0], smartVesting.address]);

#     await increaseTime(provider, vestingParams.duration.div(10).toNumber());
#     await mineBlock(provider);

#     const releasableAmount: BigNumber = await smartVesting.releasableAmount();

#     await (await smartVesting.release()).wait();

#     const after = await getTokenBalances(provider, [gToken.address], [teamAddresses[0], smartVesting.address]);

#     // Ensure the team member got more than the amount releasable shown (which will be slightly lower due to being from a previous block)

#     expect(after[teamAddresses[0]][gToken.address], "team0").to.gt(before[teamAddresses[0]][gToken.address].add(releasableAmount));
#     expect(after[smartVesting.address][gToken.address], "smartVesting").to.lt(before[smartVesting.address][gToken.address]);
#   });
# """
# def test_release_appropriate_funds(setup):
#     deployer = setup.deployer
#     gToken = setup.gToken
#     smartVesting = setup.SmartVesting
#     team = setup.team
#     # Sleep until actions are possible
#     chain.sleep(smartVesting.cliff - chain.time())



# """
#   it("Should be able to release funds after timelock expires", async function () {
#     const releaseAmount = transferAmount;

#     await increaseTime(provider, vestingParams.duration.toNumber());
#     await mineBlock(provider);

#     const releasableAmount: BigNumber = await smartVesting.releasableAmount();

#     const beneficiaryPreBalance = await gToken.balanceOf(teamAddresses[0]);
#     const timelockPreBalance = await gToken.balanceOf(smartVesting.address);

#     await (
#       await gToken
#         .connect(deployer)
#         .transfer(smartVesting.address, releaseAmount)
#     ).wait();

#     await (await smartVesting.release()).wait();

#     const beneficiaryPostBalance = await gToken.balanceOf(teamAddresses[0]);
#     const timelockPostBalance = await gToken.balanceOf(smartVesting.address);

#     expect(beneficiaryPostBalance, "Beneficiary Address").to.equal(
#       releaseAmount
#     );

#     expect(timelockPostBalance, "Timelock Address").to.equal(BigNumber.from(0));
#   });

#     """

#     """
#     it("EthGifter should be able to transfer eth", async function () {
#       const preBalances = {
#         ethGifter: await provider.getBalance(ethGifter.address),
#         deployer: await provider.getBalance(deployerAddress),
#       };

#       await (await ethGifter.requestEth(ONE_ETHER)).wait();

#       const postBalances = {
#         ethGifter: await provider.getBalance(ethGifter.address),
#         deployer: await provider.getBalance(deployerAddress),
#       };

#       expect(postBalances.ethGifter, "EthGifter loses one ETH").to.be.equal(
#         preBalances.ethGifter.sub(ONE_ETHER)
#       );
#     });
#     """

#     """
#     it("Should be able to claim ether using call function", async function () {
#       const preBalances = {
#         ethGifter: await provider.getBalance(ethGifter.address),
#         timelock: await provider.getBalance(smartVesting.address),
#       };

#       const tx = await smartVesting
#         .connect(team[0])
#         .call(
#           ethGifter.address,
#           0,
#           iEthGifter.encodeFunctionData("requestEth", [ONE_ETHER])
#         );

#       await tx.wait();

#       const postBalances = {
#         ethGifter: await provider.getBalance(ethGifter.address),
#         timelock: await provider.getBalance(smartVesting.address),
#       };

#       expect(postBalances.ethGifter, "EthGifter loses one ETH").to.be.equal(
#         preBalances.ethGifter.sub(ONE_ETHER)
#       );

#       expect(postBalances.timelock, "Timelock gains one ETH").to.be.equal(
#         preBalances.timelock.add(ONE_ETHER)
#       );
#     });
#     """

#     """
#     it("Should be able to recieve native ether payments", async function () {
#       const preBalances = {
#         deployer: await provider.getBalance(deployerAddress),
#         timelock: await provider.getBalance(smartVesting.address),
#       };

#       await (
#         await deployer.sendTransaction({
#           to: smartVesting.address,
#           value: ONE_ETHER,
#         })
#       ).wait();

#       const postBalances = {
#         deployer: await provider.getBalance(deployerAddress),
#         timelock: await provider.getBalance(smartVesting.address),
#       };

#       expect(postBalances.deployer, "Deployer loses > one ETH").to.be.lt(
#         preBalances.deployer.sub(ONE_ETHER) // Factoring in gas costs
#       );

#       expect(postBalances.timelock, "Timelock gains one ETH").to.be.equal(
#         preBalances.timelock.add(ONE_ETHER)
#       );
#     });
#     """

#     """
#     it("Should be able to send ether along with function call", async function () {
#       const preBalances = {
#         team0: await provider.getBalance(teamAddresses[0]),
#         deployer: await provider.getBalance(deployerAddress),
#       };
#       await (
#         await smartVesting
#           .connect(team[0])
#           .call(deployerAddress, ONE_ETHER, "0x", {
#             value: ONE_ETHER,
#           })
#       ).wait();

#       const postBalances = {
#         team0: await provider.getBalance(teamAddresses[0]),
#         deployer: await provider.getBalance(deployerAddress),
#       };

#       expect(postBalances.deployer).to.be.equal(
#         preBalances.deployer.add(ONE_ETHER)
#       );

#       expect(postBalances.team0).to.be.lt(preBalances.team0.sub(ONE_ETHER)); // Account for gas costs
#     });

#     """
#     """
#     it("Should be able to request tokens and increase balance of locked tokens using call function", async function () {
#       const requestTransferAction = iTokenGifter.encodeFunctionData(
#         "requestTransfer",
#         [gToken.address, tokenRequestAmount]
#       );

#       const preBalance = await gToken.balanceOf(smartVesting.address);

#       await (
#         await smartVesting
#           .connect(team[0])
#           .call(tokenGifter.address, 0, requestTransferAction)
#       ).wait();

#       const postBalance = await gToken.balanceOf(smartVesting.address);

#       expect(preBalance.add(tokenRequestAmount)).to.be.equal(postBalance);
#     });
#     """

#     it("Should not be able to transfer locked tokens using call function", async function () {
#       const transferAction = iERC20.encodeFunctionData("transfer", [
#         teamAddresses[0],
#         tokenGifterAmount,
#       ]);

#       await expect(
#         smartVesting.connect(team[0]).call(gToken.address, 0, transferAction)
#       ).to.be.revertedWith("smart-vesting/locked-balance-check");
#     });
#     """
    

    

    

    
    

    

#     """
#     """
#     it("Should be able to transfer other tokens using call function", async function () {
#       const transferAction = iERC20.encodeFunctionData("transfer", [
#         teamAddresses[0],
#         tokenGifterAmount,
#       ]);

#       const preBalance = await miscToken.balanceOf(smartVesting.address);

#       await (
#         await smartVesting
#           .connect(team[0])
#           .call(miscToken.address, 0, transferAction)
#       ).wait();

#       const postBalance = await miscToken.balanceOf(smartVesting.address);

#       expect(postBalance).to.be.equal(preBalance.sub(tokenGifterAmount));
#     });
#     """
#     """

#     """
#     it("Should not be able to claim locked tokens using claimToken()", async function () {
#       await expect(
#         smartVesting.connect(team[0]).claimToken(gToken.address)
#       ).to.be.revertedWith("smart-timelock/no-locked-token-claim");
#     });

#     it("Should be able to claim other tokens using claimToken()", async function () {
#       await (
#         await smartVesting.connect(team[0]).claimToken(miscToken.address)
#       ).wait();

#       const postBalance = await miscToken.balanceOf(smartVesting.address);
#       expect(postBalance).to.be.equal(0);
#     });
#     """

#     """
#     it("Should not be able to transfer locked tokens to contract without approval", async function () {
#       await (
#         await smartVesting
#           .connect(team[0])
#           .call(
#             gToken.address,
#             0,
#             iERC20.encodeFunctionData("approve", [
#               stakingMock.address,
#               ethers.constants.MaxUint256,
#             ])
#           )
#       ).wait();
#       let stakingAmount = utils.parseEther("100");
#       await expect(
#         smartVesting
#           .connect(team[0])
#           .call(
#             stakingMock.address,
#             0,
#             iStakingMock.encodeFunctionData("stake", [stakingAmount])
#           )
#       ).to.be.reverted;
#     });
#     """

#     """
#     it("Governor should be able to approve contracts", async function () {
#       await (
#         await smartVesting
#           .connect(governor)
#           .approveTransfer(stakingMock.address)
#       ).wait();

#       // Check event emission
#       const approveEvent = await smartVesting.queryFilter(
#         smartVesting.filters.ApproveTransfer(),
#         "latest"
#       );

#       expect(approveEvent[0].args?.to).to.be.equal(stakingMock.address);
#     });

#     """ 
    
#     """
#     it("Governor should be able to revoke approved contracts", async function () {
#       await (
#         await smartVesting
#           .connect(governor)
#           .approveTransfer(stakingMock.address)
#       ).wait();

#       await (
#         await smartVesting.connect(governor).revokeTransfer(stakingMock.address)
#       ).wait();

#       // Check event emission
#       const revokeEvent = await smartVesting.queryFilter(
#         smartVesting.filters.RevokeTransfer(),
#         "latest"
#       );

#       expect(revokeEvent[0].args?.to).to.be.equal(stakingMock.address);
#     });
#     """

#     """
#     it("Non-Governor should not be able to approve contracts", async function () {
#         await expect(
#             smartVesting.connect(team[0]).approveTransfer(stakingMock.address)
#         ).to.been.revertedWith("smart-timelock/only-governor");
#         });
#     """

#     """
#   it("Non-Governor should not be able to revoke approved contracts", async function () {
#       await expect(
#         smartVesting.connect(team[0]).revokeTransfer(stakingMock.address)
#       ).to.been.revertedWith("smart-timelock/only-governor");
#     });
#     """

#     """
#     Setup for next Batch!

#     describe("Staking on approved contract", function () {
#       let stakingAmount = utils.parseEther("100");
#       beforeEach(async function () {
#         // Approve contract on governor
#         await (
#           await smartVesting
#             .connect(governor)
#             .approveTransfer(stakingMock.address)
#         ).wait();
#         // Approve staking pool to spend tokens
#         await (
#           await smartVesting
#             .connect(team[0])
#             .call(
#               gToken.address,
#               0,
#               iERC20.encodeFunctionData("approve", [
#                 stakingMock.address,
#                 ethers.constants.MaxUint256,
#               ])
#             )
#         ).wait();
#       });
#   """

#   """
#   it("Should be able to transfer & retrieve locked tokens to contract with active approval", async function () {
#         // Send tokens to staking pool
#         const preBalances = await getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartVesting.address, stakingMock.address]
#         );

#         await (
#           await smartVesting
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).wait();

#         const postStakeBalances = await getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartVesting.address, stakingMock.address]
#         );

#         expect(
#           postStakeBalances[smartVesting.address][gToken.address].toString(),
#           "Expect timelock to lose stakingAmount of locked tokens"
#         ).to.be.equal(
#           preBalances[smartVesting.address][gToken.address]
#             .sub(stakingAmount)
#             .toString()
#         );
#         expect(
#           postStakeBalances[stakingMock.address][gToken.address],
#           "Expect staking contract to gain stakingAmount of locked tokens"
#         ).to.be.equal(stakingAmount);

#         await (
#           await smartVesting
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("unstake", [stakingAmount])
#             )
#         ).wait();

#         const postUnstakeBalances = await getTokenBalances(
#           provider,
#           [gToken.address, stakingMock.address],
#           [smartVesting.address, stakingMock.address]
#         );

#         expect(
#           postUnstakeBalances[smartVesting.address][gToken.address],
#           "Expect timelock to gain stakingAmount of locked tokens"
#         ).to.be.equal(
#           postStakeBalances[smartVesting.address][gToken.address].add(
#             stakingAmount
#           )
#         );

#         expect(
#           postUnstakeBalances[smartVesting.address][gToken.address].toString(),
#           "Expect timelock to gain stakingAmount of distributed tokens"
#         ).to.be.equal(
#           preBalances[smartVesting.address][gToken.address].toString()
#         );
#         expect(
#           postUnstakeBalances[stakingMock.address][gToken.address],
#           "Expect staking contract to lose stakingAmount of locked tokens"
#         ).to.be.equal(0);
#       });
#   """

#   """
#   it("Should not be able to retrieve staked tokens on revoked contract", async function () {
#         await (
#           await smartVesting
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).wait();

#         // Revoke contract on governor
#         await (
#           await smartVesting
#             .connect(governor)
#             .revokeTransfer(stakingMock.address)
#         ).wait();

#         await (
#           await smartVesting
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("unstake", [stakingAmount])
#             )
#         ).wait();
#       });
#     });
#   """

#   """
#   it("Should not be able to transfer locked tokens to contract with approval revoked", async function () {
#         // Revoke contract on governor
#         await (
#           await smartVesting
#             .connect(governor)
#             .revokeTransfer(stakingMock.address)
#         ).wait();

#         await expect(
#           smartVesting
#             .connect(team[0])
#             .call(
#               stakingMock.address,
#               0,
#               iStakingMock.encodeFunctionData("stake", [stakingAmount])
#             )
#         ).to.be.reverted;
#       });
#   """

#   """
#   it("Non-beneficiary should not be able to call owner-gated functions", async function () {
#     const requestTransferAction = iTokenGifter.encodeFunctionData(
#       "requestTransfer",
#       [gToken.address, tokenRequestAmount]
#     );

#     await expect(
#       smartVesting
#         .connect(minnow)
#         .call(tokenGifter.address, 0, requestTransferAction)
#     ).to.be.reverted;

#     await expect(smartVesting.connect(minnow).claimToken(gToken.address)).to.be
#       .reverted;

#     await expect(smartVesting.connect(minnow).claimToken(miscToken.address)).to
#       .be.reverted;

#     await expect(smartVesting.connect(minnow).claimEther()).to.be.reverted;
#   });
#   """