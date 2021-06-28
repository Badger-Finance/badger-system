import json

import brownie
import pytest
from brownie import *
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import GnosisSafe, multisig_success
from helpers.proxy_utils import deploy_proxy, deploy_proxy_uninitialized
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from tests.helpers import distribute_from_whales

console = Console()


@pytest.fixture(scope="function", autouse="True")
def setup():
    badger = connect_badger(badger_config.prod_json)
    deployer = accounts.load("badger_deployer")
    # distribute_from_whales(deployer)

    # Deploy Honeypot
    honeypotLogic = HoneypotMeme.deploy({"from": deployer})

    honeypot_params = DotMap(
        token=badger.token,
        amount=Wei("2500 ether"),
        nftIndicies=[97, 98, 99, 100, 101, 102],
        meme="0xe4605d46Fd0B3f8329d936a8b258D69276cBa264",
        badgerCollection="0x14dC10FA6E4878280F9CA0D9f32dDAEa8C7d4d45",
    )

    honeypot = deploy_proxy(
        "HoneypotMeme",
        HoneypotMeme.abi,
        honeypotLogic.address,
        badger.devProxyAdmin.address,
        honeypotLogic.initialize.encode_input(
            honeypot_params.token,
            honeypot_params.amount,
            honeypot_params.nftIndicies,
        ),
        deployer,
    )

    # honeypot = HoneypotMeme.deploy({"from": deployer})
    # honeypot.initialize(
    #     honeypot_params.token,
    #     honeypot_params.amount,
    #     honeypot_params.nftIndicies,
    #     {"from": deployer},
    # )

    # Transfer tokens to MEME
    multi = GnosisSafe(badger.devMultisig)
    tx = multi.execute(
        {
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.approveRecipient.encode_input(honeypot),
        },
    )

    assert badger.rewardsEscrow.isApproved(honeypot)
    assert multisig_success(tx)

    assert badger.token.balanceOf(badger.rewardsEscrow) >= honeypot_params.amount

    tx = multi.execute(
        {
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                badger.token, honeypot, honeypot_params.amount
            ),
        },
    )

    assert multisig_success(tx)
    assert badger.token.balanceOf(honeypot) == honeypot_params.amount

    # Mint MEME NFTs for deployer
    memeLtd = interface.IMemeLtd(honeypot_params.meme)

    badgerCollection = accounts.at(honeypot_params.badgerCollection, force=True)

    for index in honeypot_params.nftIndicies:
        memeLtd.mint(deployer, index, 5, "0x", {"from": badgerCollection})

    for index in honeypot_params.nftIndicies:
        assert memeLtd.balanceOf(deployer, index) > 0

    partialA = accounts[1]
    partialB = accounts[2]
    noCoiner = accounts[3]

    paritalAList = [97, 98, 99]
    paritalBList = [97, 98, 99, 100, 101]

    """
    function safeTransferFrom(
        address _from,
        address _to,
        uint256 _id,
        uint256 _amount,
        bytes calldata _data
    ) external;
    """

    for index in paritalAList:
        memeLtd.safeTransferFrom(deployer, partialA, index, 1, "0x", {"from": deployer})
        assert memeLtd.balanceOf(partialA, index) > 0

    for index in paritalBList:
        memeLtd.safeTransferFrom(deployer, partialB, index, 1, "0x", {"from": deployer})
        assert memeLtd.balanceOf(partialB, index) > 0

    return {
        "badger": badger,
        "honeypot": honeypot,
        "deployer": deployer,
        "partialA": partialA,
        "partialB": partialB,
        "noCoiner": noCoiner,
        "memeLtd": memeLtd,
        "honeypot_params": honeypot_params,
    }


def test_params(setup):
    honeypot = setup["honeypot"]
    badger = setup["badger"]

    memeLtd = setup["memeLtd"]
    honeypot_params = setup["honeypot_params"]

    assert honeypot.token() == badger.token
    assert honeypot.memeLtd() == honeypot_params.meme
    assert honeypot.honeypot() == honeypot_params.amount
    assert honeypot.nftIndicies(0) == honeypot_params.nftIndicies[0]
    assert honeypot.nftIndicies(1) == honeypot_params.nftIndicies[1]
    assert honeypot.nftIndicies(2) == honeypot_params.nftIndicies[2]
    assert honeypot.nftIndicies(3) == honeypot_params.nftIndicies[3]
    assert honeypot.nftIndicies(4) == honeypot_params.nftIndicies[4]
    assert honeypot.nftIndicies(5) == honeypot_params.nftIndicies[5]


def test_claim(setup):
    deployer = setup["deployer"]
    honeypot = setup["honeypot"]
    badger = setup["badger"]

    partialA = setup["partialA"]
    partialB = setup["partialB"]
    noCoiner = setup["noCoiner"]

    memeLtd = setup["memeLtd"]
    honeypot_params = setup["honeypot_params"]

    # Try to claim without all NFTs
    with brownie.reverts("honeypot/nft-ownership"):
        honeypot.claim({"from": partialA})

    with brownie.reverts("honeypot/nft-ownership"):
        honeypot.claim({"from": partialB})

    with brownie.reverts("honeypot/nft-ownership"):
        honeypot.claim({"from": noCoiner})

    # User that owned all NFTs in the past
    memeLtd.safeTransferFrom(
        deployer,
        partialA,
        97,
        memeLtd.balanceOf(deployer, 97),
        "0x",
        {"from": deployer},
    )

    with brownie.reverts("honeypot/nft-ownership"):
        honeypot.claim({"from": deployer})

    # Try to claim with all NFTs
    memeLtd.safeTransferFrom(
        partialA,
        deployer,
        97,
        1,
        "0x",
        {"from": partialA},
    )

    for index in honeypot_params.nftIndicies:
        assert memeLtd.balanceOf(deployer, index) > 0

    beforeBal = badger.token.balanceOf(deployer)
    honeypot.claim({"from": deployer})

    # Verify token transfer
    afterBal = badger.token.balanceOf(deployer)
    assert afterBal == beforeBal + honeypot_params.amount

    # Try to claim again without all NFTs
    with brownie.reverts("honeypot/is-claimed"):
        honeypot.claim({"from": partialB})

    beforeBal = badger.token.balanceOf(deployer)

    # Try to claim again with all NFTs
    with brownie.reverts("honeypot/is-claimed"):
        honeypot.claim({"from": deployer})

    afterBal = badger.token.balanceOf(deployer)
    assert afterBal == beforeBal
