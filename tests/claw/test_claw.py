import pytest
import random
from brownie import Wei, interface, SyntheticToken
from rich.console import Console

from helpers.constants import MaxUint256
from scripts.systems.claw_minimal import deploy_claw_minimal
from config.badger_config import claw_config
from helpers.token_utils import distribute_from_whales, distribute_test_ether
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett, clawSettSyntheticTestConfig

console = Console()


@pytest.mark.parametrize(
    "settConfig", clawSettSyntheticTestConfig,
)
def test_claw(settConfig):
    badger = badger_single_sett(settConfig, deploy=False)
    snap = SnapshotManager(badger, settConfig["id"])
    deployer = badger.deployer

    want = badger.getStrategyWant(settConfig["id"])
    sett = badger.getSett(settConfig["id"])

    depositAmount = int(want.balanceOf(deployer) * 0.8)
    assert depositAmount > 0
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})
    assert want.balanceOf(deployer) > 0

    distribute_test_ether(deployer, Wei("20 ether"))
    distribute_from_whales(deployer)

    claw = deploy_claw_minimal(deployer)
    if settConfig["id"] == "native.badger":
        _manage_position(claw, "bClaw", deployer)
    if settConfig["id"] == "sushi.sushiWbtcEth":
        _manage_position(claw, "sClaw", deployer)


# NB: The goal here is not to completely test the correctness of the UMA system but to ensure
# that we can perform basic actions on the synthetic token contracts owned by Badger.
# attempt to manage collateral position (mint/redeem/withdraw).
def _manage_position(claw, empName, user):
    empConfig = claw_config.emps[empName]
    emp = claw.emps[empName]
    collateral = interface.IERC20(empConfig.collateralAddress)
    userBalance = collateral.balanceOf(user)
    assert userBalance > 0
    collateral.approve(emp.address, userBalance, {"from": user})

    console.print("[grey]Attempting to mint synthetic tokens from collateral[/grey]")
    collateralAmount = userBalance / 4
    # Mint a synthetic amount is in $, we won't try to determine the actual dollar value between
    # the two but rather just mint a random dollar value above the min sponsor amount and a arbitrary max.
    # Min sponsor amount is $100 so let's do w/ $200 - $5000.
    syntheticAmount = random.random.randint(200, 5000) * 10 ** 18
    emp.create((collateralAmount,), (syntheticAmount,), {"from": user})

    # We don't need all of these variables but just including them here to be transparent about
    # what each one represents.
    (
        (tokensOutstanding,),
        withdrawalRequestPassTimestamp,
        (withdrawalRequestAmount,),
        (rawCollateral,),
        transferPositionRequestPassTimestamp,
    ) = emp.positions(user)

    assert tokensOutstanding > 0
    assert rawCollateral > 0

    token = SyntheticToken.at("0x89337BFb7938804c3776C9FB921EccAf5ab76758")
    token.approve(emp.address, userBalance, {"from": user})

    console.print(
        "[grey]Attempting to deposit/withdraw collateral to/from position[/grey]"
    )
    emp.deposit((collateralAmount,), {"from": user})
    # TODO: Need to add collateral from a second user to be able to withdraw from one since
    # only adding collateral from a single user means the user's collateralization ratio is the
    # global collateralization ratio.
    # emp.requestWithdrawal((collateralAmount,), {"from": user})

    console.print("[grey]Attempting to redeem collateral from position[/grey]")
    (
        (tokensOutstanding,),
        withdrawalRequestPassTimestamp,
        (withdrawalRequestAmount,),
        (rawCollateral,),
        transferPositionRequestPassTimestamp,
    ) = emp.positions(user)
    emp.redeem((tokensOutstanding,), {"from": user})

    assert token.balanceOf(user) == 0
