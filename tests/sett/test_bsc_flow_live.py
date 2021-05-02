from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.token_utils import distribute_test_ether
import brownie
import decouple
import pytest
from brownie import *
from helpers.constants import *
from helpers.proxy_utils import deploy_proxy
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.time_utils import days
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales

console = Console()

configs = {
    "native.pancakeBnbBtcb": {
        "want": registry.pancake.chefPairs.bnbBtcb,
        "token0": registry.tokens.btcb,
        "token1": registry.tokens.bnb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bnbBtcb,
    },
    "native.bBadgerBtcb": {
        "want": registry.pancake.chefPairs.bBadgerBtcb,
        "token0": registry.tokens.bBadger,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bBadgerBtcb,
    },
    "native.bDiggBtcb": {
        "want": registry.pancake.chefPairs.bDiggBtcb,
        "token0": registry.tokens.bDigg,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bDiggBtcb,
    },
}


def setup_badger(badger: BadgerSystem):
    # Set paths

    key = "native.bDiggBtcb"
    sett = badger.getSett(key)
    strategy = badger.getStrategy(key)

    multi = GnosisSafe(badger.opsMultisig)

    multi.execute(
        MultisigTxMetadata(description="Set path"),
        {
            "to": strategy.address,
            "data": strategy.setTokenSwapPath.encode_input(
                registry.pancake.cake,
                strategy.token0(),
                [registry.pancake.cake, registry.tokens.btcb, strategy.token0()],
            ),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="Set path"),
        {
            "to": strategy.address,
            "data": strategy.setTokenSwapPath.encode_input(
                registry.pancake.cake,
                strategy.token1(),
                [registry.pancake.cake, registry.tokens.btcb, strategy.token1()],
            ),
        },
    )


def deposit_withdraw_single_user_flow(badger, sett_id, user):
    controller = badger.getController("native")
    strategy = badger.getStrategy(sett_id)
    want = interface.IERC20(strategy.want())
    snap = SnapshotManager(badger, sett_id)
    sett = badger.getSett(sett_id)
    strategist = badger.deployer
    settKeeper = accounts.at(sett.keeper(), force=True)
    randomUser = accounts[6]

    # Deposit
    assert want.balanceOf(user) > 0

    depositAmount = int(want.balanceOf(user) * 0.8)
    assert depositAmount > 0

    want.approve(sett, MaxUint256, {"from": user})
    # sett.deposit(depositAmount, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": user})

    # Earn
    # with brownie.reverts("onlyAuthorizedActors"):
    #     sett.earn({"from": randomUser})

    min = sett.min()
    max = sett.max()
    remain = max - min

    # sett.earn({"from": settKeeper})
    snap.settEarn({"from": settKeeper})

    chain.sleep(15)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2, {"from": user})

    chain.sleep(10000)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2 - 1, {"from": user})


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def single_user_harvest_flow(badger: BadgerSystem, sett_id, user):
    controller = badger.getController("native")
    strategy = badger.getStrategy(sett_id)
    want = interface.IERC20(strategy.want())
    snap = SnapshotManager(badger, sett_id)
    sett = badger.getSett(sett_id)
    strategist = badger.deployer

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(user)

    depositAmount = startingBalance // 200
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": user})
    snap.settDeposit(depositAmount, {"from": user})

    assert want.balanceOf(sett) > 0
    print("want.balanceOf(sett)", want.balanceOf(sett))

    # Earn
    snap.settEarn({"from": settKeeper})

    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

    numTends = 48
    timeBetweenTends = days(365) // numTends

    console.print({"numTends": numTends, "timeBetweenTends": timeBetweenTends})

    for i in range(0, numTends):
        console.print("Tend {}".format(i))
        snap.settTend({"from": strategyKeeper})
        chain.sleep(timeBetweenTends)
        chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    # if tendable:
    #     snap.settTend({"from": strategyKeeper})

    # snap.settWithdraw(depositAmount // 2, {"from": user})

    # chain.sleep(days(3))
    # chain.mine()

    # snap.settHarvest({"from": strategyKeeper})
    # snap.settWithdraw(depositAmount // 2 - 1, {"from": user})

    assert False


def test_main():
    badger = connect_badger()
    user = accounts[0]
    distribute_test_ether(user, Wei("10 ether"))
    distribute_from_whales(user)

    setts_to_run = [
        # "native.pancakeBnbBtcb",
        "native.bDiggBtcb"
    ]
    setup_badger(badger)

    for sett_id in setts_to_run:
        # deposit_withdraw_single_user_flow(badger, sett_id, user)
        single_user_harvest_flow(badger, sett_id, user)
