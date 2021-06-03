from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import badger_single_sett, settTestConfig
from helpers.registry import registry

def state_setup(badger, settConfig):
    voterproxy = badger.mstable.voterproxy

    accounts.at(badger.deployer, force=True)
    accounts.at(voterproxy.governance(), force=True) # dualGovernance
    accounts.at(voterproxy.badgerGovernance(), force=True)
    accounts.at(voterproxy.keeper(), force=True)
    accounts.at(voterproxy.strategist(), force=True)

#@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_voterproxy_onlygovernors_permissions(settConfig):
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    voterproxy = badger.mstable.voterproxy

    nexus_governor = "0xf6ff1f7fceb2ce6d26687eaab5988b445d0b94a2"

    # Users:
    deployer = badger.deployer
    governance = voterproxy.governance()
    badgerGovernance = voterproxy.badgerGovernance()
    nexusGovernor = accounts.at(nexus_governor, force=True)
    keeper = voterproxy.keeper()
    strategist = voterproxy.strategist()
    randomUser = accounts[8]

    authorizedActors = [
        badgerGovernance,
        nexusGovernor,
    ]

    unauthorizedActors = [
        deployer,
        governance,
        keeper,
        strategist,
        randomUser
    ]

    # End Setup
    
    # exitLock
    for actor in authorizedActors:
        # onlyGovernors authorization works but reverts, as expected, on votingLockup.exit();
        with brownie.reverts("Must have something to withdraw"):
            voterproxy.exitLock({"from": actor})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernors"):
            voterproxy.exitLock({"from": actor})

    # changeRedistributionRate
    originalRate = voterproxy.redistributionRate()
    newRate = originalRate - 1000

    for actor in authorizedActors:
        voterproxy.changeRedistributionRate(newRate, {"from": actor})
        newRate = newRate - 1000

    assert voterproxy.redistributionRate() == originalRate - (len(authorizedActors) * 1000)

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernors"):
            voterproxy.changeRedistributionRate(originalRate - 1000, {"from": actor})

    # repayLoan

    # Actor loans certain amount of mta to contract
    mta = interface.IERC20(registry.mstable.mtaToken)
    mta.approve(deployer.address, MaxUint256, {"from": deployer})
    mta.approve(voterproxy.address, MaxUint256, {"from": deployer})

    originalBalance = mta.balanceOf(deployer)
    assert originalBalance > 0

    amount = mta.balanceOf(deployer.address) * 0.2
    voterproxy.loan(amount, {"from": deployer})
    assert mta.balanceOf(deployer) == originalBalance - amount

    # Actor cannot loan while holding existing loan
    with brownie.reverts("Existing loan"):
        voterproxy.loan(amount, {"from": deployer})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernors"):
            voterproxy.repayLoan(deployer.address, {"from": actor})

    # Governor repays loan
    voterproxy.repayLoan(deployer.address, {"from": authorizedActors[0]})

    assert mta.balanceOf(deployer) == originalBalance

    # Reverts when trying to repay same loan again
    with brownie.reverts("Non-existing loan"):
        voterproxy.repayLoan(deployer.address, {"from": authorizedActors[1]})
        


#@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_voterproxy_onlyharvester_permissions(settConfig):
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    voterproxy = badger.mstable.voterproxy

    nexus_governor = "0xf6ff1f7fceb2ce6d26687eaab5988b445d0b94a2"

    # Users:
    deployer = badger.deployer
    governance = voterproxy.governance()
    badgerGovernance = voterproxy.badgerGovernance()
    nexusGovernor = accounts.at(nexus_governor, force=True)
    keeper = voterproxy.keeper()
    strategist = voterproxy.strategist()
    randomUser = accounts[8]

    authorizedActors = [
        badgerGovernance,
        nexusGovernor,
        keeper,
    ]

    unauthorizedActors = [
        deployer,
        governance,
        strategist,
        randomUser
    ]

    # End Setup
    
    # harvestMta
    for actor in authorizedActors:
        # onlyGovernors authorization works but reverts, as expected, as there is no mta staked;
        with brownie.reverts("Must stake non zero amount"):
            voterproxy.harvestMta({"from": actor})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyHarvesters"):
            voterproxy.harvestMta({"from": actor})



#@pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_voterproxy_onlygovernance_permissions(settConfig):
    badger = badger_single_sett(settConfig)
    state_setup(badger, settConfig)
    voterproxy = badger.mstable.voterproxy

    settId = settConfig["id"]
    strategy = badger.getStrategy(settId)
    

    nexus_governor = "0xf6ff1f7fceb2ce6d26687eaab5988b445d0b94a2"

    # Users:
    deployer = badger.deployer
    governance = voterproxy.governance()
    badgerGovernance = voterproxy.badgerGovernance()
    nexusGovernor = accounts.at(nexus_governor, force=True)
    keeper = voterproxy.keeper()
    strategist = voterproxy.strategist()
    randomUser = accounts[8]

    authorizedActors = [
        governance,
    ]

    unauthorizedActors = [
        deployer,
        keeper,
        strategist,
        randomUser,
        badgerGovernance,
        nexusGovernor,
    ]

    # End Setup
    
    # supportStrategy
    for actor in authorizedActors:
        # onlyGovernance authorization works but reverts, as expected, 
        # since the strategy was already supported on miniDeploy.
        with brownie.reverts("Strategy already supported"):
            voterproxy.supportStrategy(
                strategy.address,
                registry.mstable.pools.imBtc.vault,
                {"from": actor}
            )

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernance"):
            voterproxy.supportStrategy(
                strategy.address,
                registry.mstable.pools.imBtc.vault,
                {"from": actor}
            )

    # createLock
    for actor in authorizedActors:
        # onlyGovernance authorization works but reverts, as expected, since there are no assets 
        # deposited on the contract
        with brownie.reverts("Must stake non zero amount"):
            voterproxy.createLock(1000, {"from": actor})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernance"):
            voterproxy.createLock(1000, {"from": actor})

    # extendLock
    for actor in authorizedActors:
        # onlyGovernance authorization works but reverts, as expected, since there is no active lock
        with brownie.reverts("Nothing is locked"):
            voterproxy.extendLock(1000, {"from": actor})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernance"):
            voterproxy.extendLock(1000, {"from": actor})

    # changeLockAddress
    dummyAddress = "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a"

    for actor in authorizedActors:
            voterproxy.changeLockAddress(dummyAddress, {"from": actor})

    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernance"):
            voterproxy.changeLockAddress(dummyAddress, {"from": actor})


    # setGovernance
    for actor in unauthorizedActors:
        with brownie.reverts("onlyGovernance"):
            voterproxy.setGovernance(randomUser, {"from": actor})

    # Change governance to randomUser
    voterproxy.setGovernance(randomUser, {"from": authorizedActors[0]})

    # Non-governance address (previous governance) attempts to change keeper
    with brownie.reverts("onlyGovernance"):
            voterproxy.setKeeper(randomUser, {"from": governance})

    # Change keeper to randomUser from newly appointed governance
    voterproxy.setKeeper(randomUser, {"from": randomUser})

    # Non-governance address (previous governance) attempts to change strategist
    with brownie.reverts("onlyGovernance"):
            voterproxy.setStrategist(randomUser, {"from": governance})

    # Change strategist to randomUser from newly appointed governance
    voterproxy.setStrategist(randomUser, {"from": randomUser})