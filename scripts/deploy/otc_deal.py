from helpers.token_utils import (
    diff_token_balances,
    distribute_from_whales,
    distribute_test_ether,
    get_token_balances,
    print_balances,
)
from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from config.active_emissions import emissions, get_active_rewards_schedule
import datetime
import json
import os
from scripts.actions.helpers.GeyserDistributor import GeyserDistributor
from scripts.actions.helpers.StakingRewardsDistributor import StakingRewardsDistributor
import time
import warnings
import decouple
import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    to_digg_shares,
    val,
)
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()


def main():
    badger = connect_badger("deploy-final.json")

    test_user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    distribute_test_ether(test_user, Wei("20 ether"))
    distribute_from_whales(test_user, assets=["bBadger", "badger", "usdc"])

    rest = get_active_rewards_schedule(badger)
    usdc = interface.IERC20(registry.tokens.usdc)

    usdc_per_badger = 40.37 * 0.75
    usdc_total = 13386240

    multi = GnosisSafe(badger.devMultisig)

    badger_total_scaled = usdc_total / usdc_per_badger

    badger_total = Wei(str(badger_total_scaled) + " ether")

    bBadger = badger.getSett("native.badger")

    ppfs = bBadger.getPricePerFullShare()

    bBadger_total = int(badger_total / ppfs * 10 ** 18)

    badger_total = Wei(str(badger_total_scaled) + " ether")

    console.print(
        {
            "TRADE": "BASED",
            "usdc_per_badger": usdc_per_badger,
            "usdc_total": usdc_total,
            "badger_total_scaled": badger_total_scaled,
            "badger_total": badger_total,
            "ppfs": ppfs,
            "bBadger_total": str(bBadger_total),
        }
    )

    params = {
        "beneficiary": "0x3159b46a7829a0dbfa856888af768fe7146e7418",
        "duration": days(182),
        "usdcAmount": usdc_total * 10 ** 6,
        "bBadgerAmount": bBadger_total,
        # "usdcAmount": 0,
        # "bBadgerAmount": 0,
    }

    console.print(params)

    # # Oxb1 Test
    beneficiary = accounts.at(params["beneficiary"], force=True)

    escrow = OtcEscrow.at("0x7163fB2fA38Ea3BBc1F8525F3d8D0417C0c9d903")

    # bBadger.transfer(badger.devMultisig, Wei("100000 ether"), {"from": test_user})

    pre = get_token_balances(
        [usdc, bBadger], [test_user, escrow, badger.devMultisig, beneficiary]
    )
    pre.print()

    # assert usdc.balanceOf(params["beneficiary"]) >= params["usdcAmount"]

    # multi.execute(MultisigTxMetadata(description="Transfer to 0xb1"), {
    #     "to": bBadger.address,
    #     "data": bBadger.transfer.encode_input(escrow, bBadger_total + Wei("1000 ether"))
    # })

    # assert usdc.allowance(beneficiary, escrow) >= params["usdcAmount"]

    # usdc.approve(escrow, params["usdcAmount"], {"from": beneficiary})
    # tx = escrow.swap({"from": beneficiary})

    tx = multi.execute(
        MultisigTxMetadata(description="Swap"),
        {"to": escrow.address, "data": escrow.swap.encode_input()},
        print_output=False,
    )

    chain.mine()

    print(tx.call_trace())

    vesting = interface.ITokenTimelock(tx.events["VestingDeployed"][0]["vesting"])

    console.print(
        {
            "token": vesting.token(),
            "beneficiary": vesting.beneficiary(),
            "releaseTime": to_utc_date(vesting.releaseTime()),
        }
    )

    post = get_token_balances(
        [usdc, bBadger], [test_user, escrow, badger.devMultisig, beneficiary]
    )

    diff_token_balances(pre, post)
    try:
        vesting.release({"from": test_user})
    except:
        print("early vest failed!")

    chain.sleep(days(182))
    chain.mine()
    # End

    vesting.release({"from": test_user})

    post = get_token_balances(
        [usdc, bBadger], [test_user, escrow, badger.devMultisig, beneficiary]
    )

    diff_token_balances(pre, post)

    return

    escrow = OtcEscrow.deploy(
        params["beneficiary"],
        params["duration"],
        params["usdcAmount"],
        params["bBadgerAmount"],
        {"from": badger.deployer},
    )

    beneficiary = accounts.at(params["beneficiary"], force=True)
    usdc.transfer(beneficiary, params["usdcAmount"], {"from": test_user})
    usdc.transfer(beneficiary, 1500000000000, {"from": test_user})

    badger.token.transfer(badger.devMultisig, badger_total, {"from": test_user})

    multi.execute(
        MultisigTxMetadata(description="Whitelist Multi"),
        {
            "to": bBadger.address,
            "data": bBadger.approveContractAccess.encode_input(badger.devMultisig),
        },
    )

    assert badger.token.balanceOf(badger.devMultisig) > Wei("100 ether")

    multi.execute(
        MultisigTxMetadata(description="Approve bBadger Contract"),
        {
            "to": badger.token.address,
            "data": badger.token.approve.encode_input(bBadger, badger_total),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="Deposit"),
        {"to": bBadger.address, "data": bBadger.deposit.encode_input(badger_total)},
    )

    console.print(
        "bBadger.balanceOf(badger.devMultisig)",
        bBadger.balanceOf(badger.devMultisig),
        params["bBadgerAmount"],
        params["bBadgerAmount"] - bBadger.balanceOf(badger.devMultisig),
    )
    assert bBadger.balanceOf(badger.devMultisig) >= params["bBadgerAmount"]

    chain.mine()
    chain.sleep(14)
    chain.mine()

    multi.execute(
        MultisigTxMetadata(description="Transfer"),
        {
            "to": bBadger.address,
            "data": bBadger.transfer.encode_input(escrow, params["bBadgerAmount"]),
        },
    )

    assert bBadger.balanceOf(escrow) == params["bBadgerAmount"]

    multi.execute(
        MultisigTxMetadata(description="Revoke"),
        {"to": escrow.address, "data": escrow.revoke.encode_input()},
    )

    assert bBadger.balanceOf(escrow) == 0
    assert bBadger.balanceOf(badger.devMultisig) >= params["bBadgerAmount"]

    print(bBadger.balanceOf(badger.devMultisig))

    bBadger.transfer(escrow, params["bBadgerAmount"], {"from": test_user})

    pre = get_token_balances(
        [usdc, bBadger], [test_user, escrow, badger.devMultisig, beneficiary]
    )
    console.print(pre)

    assert usdc.balanceOf(beneficiary) >= params["usdcAmount"]
    assert bBadger.balanceOf(escrow) == params["bBadgerAmount"]

    usdc.approve(escrow, params["usdcAmount"], {"from": beneficiary})
    tx = escrow.swap({"from": beneficiary})

    post = get_token_balances(
        [usdc, bBadger], [test_user, escrow, badger.devMultisig, beneficiary]
    )

    console.print(tx.events)
    post.print()
    diff_token_balances(pre, post)

    vesting = interface.ITokenTimelock(tx.events["VestingDeployed"][0]["vesting"])

    console.print(
        {
            "token": vesting.token(),
            "beneficiary": vesting.beneficiary(),
            "releaseTime": to_utc_date(vesting.releaseTime()),
        }
    )

    chain.sleep(days(365))
    chain.mine()

    vesting.release({"from": test_user})
