import pytest
from brownie import *
from helpers.time_utils import days, hours
from helpers.constants import MaxUint256
from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from tests.conftest import badger_single_sett, stabilizeTestConfig
from helpers.token_utils import distribute_from_whales
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.badger_system import BadgerSystem
from helpers.registry import registry
from rich.console import Console
from config.badger_config import digg_config

console = Console()

# Rebase constants pulled directly from `UFragmentsPolicy.sol`.
# 15 minute rebase window at 8pm UTC everyday.
REBASE_WINDOW_OFFSET_SEC = digg_config.rebaseWindowOffsetSec
MIN_REBASE_TIME_INTERVAL_SEC = digg_config.minRebaseTimeIntervalSec
DAY = 24 * 60 * 60

@pytest.mark.parametrize(
    "settConfig", stabilizeTestConfig,
)
def test_single_user_rebalance_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.vault
    strategy = badger.strategy
    controller = badger.controller

    want = interface.IDigg(strategy.want())

    # Oracles
    diggOracle = interface.AggregatorV3Interface("0x418a6C98CD5B8275955f08F0b8C1c6838c8b1685")
    btcOracle = interface.AggregatorV3Interface("0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c")

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = DiggSnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    distribute_from_whales(randomUser, 0.8, "digg")

    startingBalance = want.balanceOf(randomUser)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    print("Time Start: ", chain.time())
    # Deposit
    want.approve(sett, MaxUint256, {"from": randomUser})
    snap.settDeposit(depositAmount, {"from": randomUser})

    # Chain sleeps for a very small time to stay within Oracle price feed threshold
    chain.sleep(hours(0.25))
    chain.mine()

    # Earn
    snap.settEarn({"from": settKeeper})

    chain.sleep(hours(0.25))
    chain.mine()

    # Rebase
    # Push/rebase on an exchange rate of 1.2
    snap.rebase(1.2 * 10 ** 18, {"from": deployer})
    print("Time After First Rebase: ", chain.time())

    print(diggOracle.latestRoundData())

    # Rebalance
    snap.rebalance({"from": settKeeper})

    chain.sleep(hours(0.25))
    chain.mine()

    # Earn
    snap.settEarn({"from": settKeeper})

    chain.sleep(hours(0.25))
    chain.mine()

    # Rebase
    # Push/rebase on an exchange rate of 0.6
    snap.rebase(0.6 * 10 ** 18, {"from": deployer})
    print("Time After First Rebase: ", chain.time())

    print(diggOracle.latestRoundData())

    # Rebalance
    snap.rebalance({"from": settKeeper})

    chain.sleep(hours(0.25))
    chain.mine()

    # Withdraw
    amount = sett.balanceOf(randomUser.address)
    snap.settWithdraw(amount // 2, {"from": randomUser})

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

        supplyAfter = digg.token.totalSupply()

        print("spfAfter", digg.token._sharesPerFragment())
        print("supplyAfter", supplyAfter)
        print("supplyChange", supplyAfter / supplyBefore)
        print("supplyChangeOtherWay", supplyBefore / supplyAfter)

        print("pair after", pair.getReserves())
        print("uniPair after", uniPair.getReserves())
    else:
        console.print("[white]===== No Rebase =====[/white]")


def _shift_into_next_rebase_window(badger: BadgerSystem):
    digg = badger.digg

    utcnow_unix_offset_secs = chain.time() % MIN_REBASE_TIME_INTERVAL_SEC

    if utcnow_unix_offset_secs < REBASE_WINDOW_OFFSET_SEC:
        # Shift to 1hr before rebase window and fetch Oracle's data
        chain.sleep(REBASE_WINDOW_OFFSET_SEC - utcnow_unix_offset_secs - hours(1))
        badger.digg.chainlinkForwarder.getThePrice({"from": badger.deployer})

        # Shift to rebase window
        chain.sleep(hours(1))

        chain.mine()

    else:
        # Shift to the end of the day
        secs_remaining_in_day = DAY - utcnow_unix_offset_secs
        chain.sleep(secs_remaining_in_day)

        # Repeat process
        utcnow_unix_offset_secs = chain.time() % MIN_REBASE_TIME_INTERVAL_SEC
        
        # Shift to 1hr before rebase window and fetch Oracle's data
        chain.sleep(REBASE_WINDOW_OFFSET_SEC - utcnow_unix_offset_secs - hours(1))
        badger.digg.chainlinkForwarder.getThePrice({"from": badger.deployer})

        # Shift to rebase window
        chain.sleep(hours(1))

        chain.mine()

