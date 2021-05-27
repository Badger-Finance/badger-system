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

    # Harvest
    chain.sleep(hours(0.1))
    chain.mine()
    snap.settHarvest({"from": strategyKeeper})

    # Withdraw half
    snap.settWithdraw(depositAmount // 2, {"from": deployer})
    
    # KeepMinRatio to maintain collateralization safe enough from liquidation
    currentRatio = strategy.currentRatio()
    safeRatio = currentRatio + 20
    strategy.setMinRatio(safeRatio, {"from": governance})
    strategy.keepMinRatio({"from": governance})
    assert strategy.currentRatio() > safeRatio
    
    # sugar-daddy usdp discrepancy due to accrued interest in Unit Protocol
    debtTotal = strategy.getDebtBalance()
    curveGauge = interface.ICurveGauge("0x055be5DDB7A925BfEF3417FC157f53CA77cA7222")
    usdp3crvInGauge = curveGauge.balanceOf(strategy)
    curvePool = interface.ICurveFi("0x42d7025938bEc20B69cBae5A77421082407f053A")    
    usdpOfPool = curvePool.calc_withdraw_one_coin(usdp3crvInGauge,0)
    sugar = (debtTotal - usdpOfPool) * 2
    if(sugar > 0):
       usdpToken = interface.IERC20("0x1456688345527bE1f37E9e627DA0837D6f08C925")
       usdpToken.transfer(strategy, sugar, {'from':deployer})  
       print("sugar debt=", sugar)       

    # Harvest again
    chain.sleep(hours(0.1))
    chain.mine()
    snap.settHarvest({"from": strategyKeeper})
    
    # Withdraw all
    wantInSettBalance = sett.getPricePerFullShare() * sett.totalSupply() / 1e18
    print("wantInSett=", wantInSettBalance)
    print("wantInStrategy=", strategy.balanceOfPool())
    print("pricePerFullShare=", sett.getPricePerFullShare())
    wantToWithdraw = sett.balanceOf(deployer) * sett.getPricePerFullShare() / 1e18
    print("wantToWithdraw=", wantToWithdraw)
    assert wantToWithdraw <= wantInSettBalance
    
    renbtcToken = interface.IERC20("0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D")
    controller.withdrawAll(renbtcToken, {"from": deployer})
    
    snap.settWithdrawAll({"from": deployer})

    assert True


