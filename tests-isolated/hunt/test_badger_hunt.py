# import json

# import brownie
# import pytest
# from brownie import *
# from config.badger_config import badger_config
# from helpers.constants import *
# from helpers.gnosis_safe import convert_to_test_mode, exec_direct
# from helpers.time_utils import days
# from rich.console import Console
# from scripts.systems.badger_system import connect_badger

# console = Console()

# with open("merkle/airdrop.json") as f:
#     Airdrop = json.load(f)


# @pytest.fixture(scope="function", autouse="True")
# def setup(badger_hunt_unit):
#     chain
#     return badger_hunt_unit


# def upgrade_hunt():
#     system = connect_badger("deploy-final.json")
#     deployer = system.deployer
#     multisig = system.devMultisig
#     admin = system.devProxyAdmin
#     contract = system.badgerHunt

#     newLogic = BadgerHunt.deploy({"from": deployer})
#     encoded = admin.upgrade.encode_input(contract, newLogic)

#     convert_to_test_mode(multisig)
#     exec_direct(multisig, {"to": admin.address, "data": encoded}, deployer)

#     return system


# # @pytest.mark.skip()
# def test_initial_parameters(setup):
#     """
#     Ensure all values are written correctly
#     """
#     connect = upgrade_hunt()
#     hunt = connect.badgerHunt
#     badger = connect.token
#     deployer = connect.deployer

#     assert hunt.owner() == connect.devMultisig
#     assert hunt.token() == setup.token
#     assert hunt.rewardsEscrow() == setup.rewardsEscrow
#     assert hunt.epochDuration() == days(1)
#     assert hunt.gracePeriod() == days(2)
#     assert hunt.rewardReductionPerEpoch() == 2000
#     assert hunt.currentRewardRate() == 10000
#     assert hunt.finalEpoch() == 4


# # @pytest.mark.skip()
# def test_claims_e2e(setup):
#     """
#     Ensure claims flow
#     - Each user can claim once
#     - User without a claim shouldn't be able to claim
#     - User with wrong proof shouldn't be able to claim
#     - User should not be able to claim twice
#     - User should be tracked correctly as claimed or not claimed
#     - Epochs should update at appropriate times
#     - Epochs, times, and reward percentages should update correctly with the passage of time
#     - Excess rewards should go to RewardsEscrow
#     """
#     connect = upgrade_hunt()
#     hunt = connect.badgerHunt
#     badger = connect.token
#     deployer = connect.deployer

#     users = [
#         "0x0e66CF7a7E7A7F4574670f6c2c9d463e1478a06C",
#     ]

#     MAX_BPS = hunt.MAX_BPS()

#     for user in users:
#         accounts.at(user, force=True)

#         claim = Airdrop["claims"][user]
#         index = claim["index"]
#         amount = int(claim["amount"], 16)
#         proof = claim["proof"]

#         console.log(locals())

#         # Should not be able to claim with invalid address
#         with brownie.reverts():
#             hunt.claim(index, deployer.address, amount, proof, {"from": user})

#         # Should not be able to claim with invalid index
#         with brownie.reverts():
#             hunt.claim(index + 1, user, amount, proof, {"from": user})

#         # Should not be able to claim with invalid amount
#         with brownie.reverts():
#             hunt.claim(index, user, amount + 1, proof, {"from": user})

#         # Should not be able to claim from another account
#         with brownie.reverts():
#             hunt.claim(index, user, amount, proof, {"from": deployer})

#         preBalance = badger.balanceOf(user)

#         assert badger.balanceOf(hunt) > amount

#         hunt.claim(index, user, amount, proof, {"from": user})

#         # Should not be able to claim twice
#         with brownie.reverts():
#             hunt.claim(index, user, amount, proof, {"from": user})

#         with brownie.reverts():
#             hunt.setGracePeriod(days(3), {"from": user})

#         postBalance = badger.balanceOf(user)
#         rewardsRate = hunt.currentRewardRate()
#         expectedRewards = int(amount * rewardsRate // MAX_BPS)

#         assert preBalance + expectedRewards == postBalance


# def test_claims_e2e_after_extension(setup):
#     connect = upgrade_hunt()
#     hunt = connect.badgerHunt
#     badger = connect.token
#     deployer = connect.deployer

#     users = ["0x0e66CF7a7E7A7F4574670f6c2c9d463e1478a06C"]

#     MAX_BPS = hunt.MAX_BPS()

#     exec_direct(
#         connect.devMultisig,
#         {"to": hunt.address, "data": hunt.setGracePeriod.encode_input(days(3)),},
#         deployer,
#     )
#     # hunt.setGracePeriod(days(3), {'from': deployer})
#     assert hunt.gracePeriod() == days(3)

#     for user in users:
#         accounts.at(user, force=True)

#         if hunt.isClaimed(user):
#             print("Skip ", user)
#             continue

#         claim = Airdrop["claims"][user]
#         index = claim["index"]
#         amount = int(claim["amount"], 16)
#         proof = claim["proof"]

#         console.log(locals())

#         # Should not be able to claim with invalid address
#         with brownie.reverts():
#             hunt.claim(index, deployer.address, amount, proof, {"from": user})

#         # Should not be able to claim with invalid index
#         with brownie.reverts():
#             hunt.claim(index + 1, user, amount, proof, {"from": user})

#         # Should not be able to claim with invalid amount
#         with brownie.reverts():
#             hunt.claim(index, user, amount + 1, proof, {"from": user})

#         # Should not be able to claim from another account
#         with brownie.reverts():
#             hunt.claim(index, user, amount, proof, {"from": deployer})

#         preBalance = badger.balanceOf(user)

#         hunt.claim(index, user, amount, proof, {"from": user})

#         # Should not be able to claim twice
#         with brownie.reverts():
#             hunt.claim(index, user, amount, proof, {"from": user})

#         with brownie.reverts():
#             hunt.setGracePeriod(days(3), {"from": user})

#         postBalance = badger.balanceOf(user)
#         rewardsRate = hunt.currentRewardRate()
#         assert hunt.currentRewardRate() == MAX_BPS
#         expectedRewards = int(amount * rewardsRate // MAX_BPS)

#         assert preBalance + expectedRewards == postBalance


# @pytest.mark.skip()
# def test_all_claims_full_amount(setup):
#     badger = setup.token
#     hunt = setup.badgerHunt
#     badger = setup.token
#     deployer = setup.deployer
#     MAX_BPS = hunt.MAX_BPS()

#     """
#     Ensure all claims
#     - Each user should be able to claim their amount
#     - Total claimed @ day 1 should equal total hunt supplys
#     """
#     totalClaimed = 0
#     expectedTotal = badger_config.huntParams.badgerAmount

#     assert badger.balanceOf(hunt) == expectedTotal

#     for user, userData in Airdrop["claims"].items():
#         # Unlock their account (force=True)
#         accounts.at(user, force=True)

#         claim = Airdrop["claims"][user]
#         index = claim["index"]
#         amount = int(claim["amount"], 16)
#         proof = claim["proof"]

#         # Make their claim
#         preBalance = badger.balanceOf(user)

#         hunt.claim(index, user, amount, proof, {"from": user})

#         # Should not be able to claim twice
#         with brownie.reverts():
#             hunt.claim(index, user, amount, proof, {"from": user})

#         postBalance = badger.balanceOf(user)
#         rewardsRate = hunt.currentRewardRate()
#         expectedRewards = int(amount * rewardsRate // MAX_BPS)

#         # Ensure their claim is correct
#         assert preBalance + expectedRewards == postBalance

#         # Track total claimed
#         totalClaimed += expectedRewards

#     assert totalClaimed == expectedTotal


# def read_badger_hunt(hunt):
#     return {
#         "gracePeriodEnd": hunt.getGracePeriodEnd(),
#         "claimsStartTime": hunt.getClaimsStartTime(),
#         "nextEpochStart": hunt.getNextEpochStart(),
#         "currentEpoch": hunt.getCurrentEpoch(),
#         "currentRewardsRate": hunt.getCurrentRewardsRate(),
#         "nextEpochRewardsRate": hunt.getNextEpochRewardsRate(),
#     }


# def test_epoch_evolution(setup):
#     """
#     * Ensure each epoch updates at expected times
#     * Ensure correct rewardsRate, time related read methods for each epoch
#     """
#     badger = setup.token
#     hunt = setup.badgerHunt
#     deployer = setup.deployer
#     MAX_BPS = hunt.MAX_BPS()

#     # Static reads
#     startTime = hunt.claimsStart()

#     epochDuration = hunt.epochDuration()
#     rewardReductionPerEpoch = hunt.rewardReductionPerEpoch()
#     currentRewardRate = hunt.currentRewardRate()
#     finalEpoch = hunt.finalEpoch()
#     rewardsEscrow = hunt.rewardsEscrow()
#     hunt.setGracePeriod(days(3), {"from": deployer})
#     gracePeriod = hunt.gracePeriod()
#     assert gracePeriod == days(3)
#     assert epochDuration == days(1)
#     assert rewardReductionPerEpoch == 2000
#     assert currentRewardRate == 10000
#     assert finalEpoch == 4

#     epochData = read_badger_hunt(hunt)

#     timeTillNextEpoch = startTime + gracePeriod - chain.time()

#     # First Epoch
#     assert epochData["claimsStartTime"] == startTime
#     assert epochData["gracePeriodEnd"] == startTime + gracePeriod
#     assert epochData["nextEpochStart"] == startTime + gracePeriod
#     assert epochData["currentEpoch"] == 0
#     assert epochData["currentRewardsRate"] == 10000
#     assert epochData["nextEpochRewardsRate"] == 8000

#     print(chain.time())
#     console.log(locals())

#     # Subsequent Epochs
#     for i in range(1, 4):
#         chain.sleep(timeTillNextEpoch)
#         chain.mine()
#         epochData = read_badger_hunt(hunt)

#         assert epochData["currentEpoch"] == i
#         assert epochData["claimsStartTime"] == startTime
#         assert epochData["gracePeriodEnd"] == startTime + gracePeriod
#         assert epochData["nextEpochStart"] == startTime + gracePeriod + int(
#             epochDuration * i
#         )
#         assert epochData["currentRewardsRate"] == 10000 - (i * rewardReductionPerEpoch)
#         assert epochData["nextEpochRewardsRate"] == 10000 - (
#             (i + 1) * rewardReductionPerEpoch
#         )

#         timeTillNextEpoch = epochData["nextEpochStart"] - chain.time()
