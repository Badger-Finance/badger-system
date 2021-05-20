import json
import os
import time

import brownie
import decouple
from brownie import *
from helpers.constants import *
from helpers.proxy_utils import deploy_proxy
from helpers.registry import registry
from helpers.time_utils import days
from helpers.token_utils import (
    distribute_from_whales,
    distribute_meme_nfts,
    distribute_test_ether,
)
from rich.console import Console
from scripts.systems.badger_system import connect_badger

token_registry = registry.tokens

console = Console()


def test_gitcoin_round_8_flow():
    gitcoin_round_8_flow()


def main():
    gitcoin_round_8_flow()


def gitcoin_round_8_flow():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    badger = connect_badger(
        "deploy-final.json", load_deployer=False, load_keeper=False, load_guardian=False
    )

    console.print("[blue]=== 🦡 Test ENV for account {} 🦡 ===[/blue]".format(user))

    # ===== Transfer test assets to User =====
    distribute_test_ether(user, Wei("20 ether"))
    distribute_test_ether(badger.deployer, Wei("20 ether"))
    distribute_from_whales(user)

    gitcoin_airdrop_root = (
        "0xcd18c32591078dcb6686c5b4db427b7241f5f1209e79e2e2a31e17c1382dd3e2"
    )
    bBadger = badger.getSett("native.badger")

    with open("./airdrop/gitcoin-round-8-airdrop.json") as f:
        merkle = json.load(f)

    # ===== Local Setup =====
    airdropLogic = AirdropDistributor.at("0x5c087cbb48f869f636ff11b385884296146fb505")
    # airdropProxy = deploy_proxy(
    #     "AirdropDistributor",
    #     AirdropDistributor.abi,
    #     airdropLogic.address,
    #     badger.opsProxyAdmin.address,
    #     airdropLogic.initialize.encode_input(
    #         bBadger,
    #         gitcoin_airdrop_root,
    #         badger.rewardsEscrow,
    #         chain.time() + days(7),
    #         ["0x5b908E3a23823Fd9Da157726736BACBFf472976a"],
    #     ),
    # )

    account = accounts.load("badger_proxy_deployer")

    airdropProxy = AirdropDistributor.at("0xd17c7effa924b55951e0f6d555b3a3ea34451179")
    bBadger.transfer(airdropProxy, bBadger.balanceOf(account), {"from": account})

    console.print("airdropProxy", airdropProxy)

    console.print("bBadger", bBadger.balanceOf(user))

    # assert airdropProxy.isClaimTester(user) == True
    assert airdropProxy.isClaimTester(badger.guardian) == False

    # airdropProxy.unpause({"from": badger.guardian})

    other_claim = merkle["claims"]["0x5b908E3a23823Fd9Da157726736BACBFf472976a".lower()]
    user_claim = merkle["claims"][user.address.lower()]
    amount = int(user_claim["amount"], 16)

    before = bBadger.balanceOf(user)

    with brownie.reverts("Ownable: caller is not the owner"):
        airdropProxy.openAirdrop({"from": user})

    tester = accounts.at("0x5b908E3a23823Fd9Da157726736BACBFf472976a", force=True)

    print(bBadger.balanceOf(tester))

    airdropProxy.claim(
        other_claim["index"],
        tester.address,
        int(other_claim["amount"], 16),
        other_claim["proof"],
        {"from": tester},
    )

    print(bBadger.balanceOf(tester))

    with brownie.reverts("onlyClaimTesters"):
        airdropProxy.claim(
            user_claim["index"],
            user.address,
            amount,
            other_claim["proof"],
            {"from": user},
        )

    with brownie.reverts("Ownable: caller is not the owner"):
        airdropProxy.reclaim({"from": user})

    airdropProxy.openAirdrop({"from": badger.guardian})

    with brownie.reverts("AirdropDistributor: Invalid proof."):
        airdropProxy.claim(
            user_claim["index"],
            user.address,
            amount,
            other_claim["proof"],
            {"from": user},
        )

    airdropProxy.claim(
        user_claim["index"], user.address, amount, user_claim["proof"], {"from": user},
    )

    with brownie.reverts("AirdropDistributor: Drop already claimed."):
        airdropProxy.claim(
            user_claim["index"],
            user.address,
            amount,
            user_claim["proof"],
            {"from": user},
        )

    after = bBadger.balanceOf(user)

    assert after == before + amount
    assert False
