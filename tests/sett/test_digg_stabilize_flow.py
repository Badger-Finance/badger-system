import pytest
from brownie import *
from helpers.time_utils import days, hours
from helpers.constants import MaxUint256
from helpers.sett.DiggStabilizerSnapshotManager import DiggStabilizerSnapshotManager
from tests.conftest import badger_single_sett, stabilizeTestConfig
from helpers.token_utils import distribute_from_whales
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.badger_system import BadgerSystem
from helpers.registry import registry
from rich.console import Console

console = Console()

@pytest.mark.parametrize(
    "settConfig", stabilizeTestConfig,
)
def test_single_user_rebalance_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.vault
    strategy = badger.strategy
    controller = badger.controller

    want = interface.IDigg(strategy.want())

    print("Sett", sett.address)
    print("strategy", strategy.address)
    print("controller", controller.address)
    print("want", want.address)

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = DiggStabilizerSnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    distribute_from_whales(randomUser, 0.8, "digg")

    startingBalance = want.balanceOf(randomUser)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": randomUser})
    snap.settDeposit(depositAmount, {"from": randomUser})

    chain.sleep(days(1))
    chain.mine()

    # Earn
    snap.settEarn({"from": settKeeper})

    chain.sleep(days(1))
    chain.mine()

    # Push/rebase on an exchange rate of 1.2 (DIGG trading at 1.2x BTC)
    rebase(badger, deployer)

    chain.sleep(days(1))
    chain.mine()

    # Rebalance
    snap.rebalance({"from": settKeeper})

    assert False

def rebase(badger: BadgerSystem, account):
    digg = badger.digg
    supplyBefore = digg.token.totalSupply()

    print("spfBefore", digg.token._sharesPerFragment())
    print("supplyBefore", digg.token.totalSupply())

    print(digg.cpiMedianOracle.getData.call())

    sushi = SushiswapSystem()
    pair = sushi.getPair(digg.token, registry.tokens.wbtc)

    uni = UniswapSystem()
    uniPair = uni.getPair(digg.token, registry.tokens.wbtc)

    last_rebase_time = digg.uFragmentsPolicy.lastRebaseTimestampSec()
    in_rebase_window = digg.uFragmentsPolicy.inRebaseWindow()
    now = chain.time()

    time_since_last_rebase = now - last_rebase_time

    console.print(
        {
            "last_rebase_time": last_rebase_time,
            "in_rebase_window": in_rebase_window,
            "now": now,
            "time_since_last_rebase": time_since_last_rebase,
        }
    )

    # Rebase if sufficient time has passed since last rebase and we are in the window.
    # Give adequate time between TX attempts
    if time_since_last_rebase > hours(2) and in_rebase_window:
        console.print("[bold yellow]===== 📈 Rebase! 📉=====[/bold yellow]")
        print("pair before", pair.getReserves())
        print("uniPair before", uniPair.getReserves())

        tx = digg.orchestrator.rebase({"from": account})

        if rpc.is_active():
            chain.mine()
            print(tx.call_trace())
            print(tx.events)

        supplyAfter = digg.token.totalSupply()

        print("spfAfter", digg.token._sharesPerFragment())
        print("supplyAfter", supplyAfter)
        print("supplyChange", supplyAfter / supplyBefore)
        print("supplyChangeOtherWay", supplyBefore / supplyAfter)

        print("pair after", pair.getReserves())
        print("uniPair after", uniPair.getReserves())
    else:
        console.print("[white]===== No Rebase =====[/white]")
