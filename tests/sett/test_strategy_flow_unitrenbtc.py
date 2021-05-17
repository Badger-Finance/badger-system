from helpers.time_utils import days, hours
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales, getTokenMetadata
from tests.test_recorder import EventRecord, TestRecorder
from rich.console import Console

console = Console()


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_single_user_harvest_flow(settConfig):
    badger = badger_single_sett(settConfig)

    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    
    governance = strategy.governance()

    tendable = strategy.isTendable()

    distribute_from_whales(deployer);
    startingBalance = want.balanceOf(deployer)

    depositAmount = 50 * 1e8 # renBTC decimal is 8
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    assert want.balanceOf(sett) > 0
    print("want.balanceOf(sett)", want.balanceOf(sett))

    # Earn
    snap.settEarn({"from": settKeeper})

    chain.sleep(hours(0.1))
    chain.mine()

    # Harvest
    snap.settHarvest({"from": strategyKeeper})

    chain.sleep(hours(0.1))
    chain.mine()

    # Withdraw half
    snap.settWithdraw(depositAmount // 2, {"from": deployer})
    
    # KeepMinRatio to maintain collateralization safe enough from liquidation
    currentRatio = strategy.currentRatio()
    safeRatio = currentRatio + 20
    strategy.setMinRatio(safeRatio, {"from": governance})
    strategy.keepMinRatio({"from": governance})
    assert strategy.currentRatio() > safeRatio

    chain.sleep(hours(0.1))
    chain.mine()

    # Harvest again
    snap.settHarvest({"from": strategyKeeper})
    
    # sugar-daddy usdp discrepancy due to accrued interest in Unit Protocol
    usdpToken = interface.IERC20Upgradeable("0x1456688345527bE1f37E9e627DA0837D6f08C925")
    debtTotal = strategy.getDebtBalance()
    usdpOfPool = strategy.usdpOfPool()
    usdpToken.transfer(strategy, (debtTotal - usdpOfPool) * 2, {'from':deployer})
    
    # Withdraw rest
    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})

    assert True


