from helpers.gnosis_safe import exec_direct
from scripts.systems.uniswap_system import UniswapSystem
import pytest
from brownie import *
from dotmap import DotMap
from helpers.registry import whale_registry

def get_token_balances(accounts, tokens):
    balances = DotMap()
    for token in tokens:
        for account in accounts:
            balances.token.account = token.balanceOf(account)
    return balances


def distribute_test_assets(badger):
    distribute_rewards_escrow(
        badger, badger.token, badger.deployer, Wei("100000 ether")
    )
    distribute_from_whales(badger, badger.deployer)


def create_uniswap_pair(token0, token1, signer):
    uniswap = UniswapSystem()
    if not uniswap.hasPair(token0, token1):
        uniswap.createPair(token0, token1, signer)
    
    return uniswap.getPair(token0, token1)

def distribute_from_whales(badger, recipient):
    print(len(whale_registry.items()))
    for key, whale in whale_registry.items():
        print(whale.token)
        if whale.token:
            token = interface.IERC20(whale.token)
            token.transfer(
                recipient, token.balanceOf(whale.whale), {"from": whale.whale}
            )


def distribute_rewards_escrow(badger, token, recipient, amount):
    """
    Distribute Badger from rewardsEscrow
    """

    # Approve recipient for expenditure
    if not badger.rewardsEscrow.isApproved(recipient):
        exec_direct(
            badger.devMultisig,
            {
                "to": badger.rewardsEscrow,
                "data": badger.rewardsEscrow.approveRecipient.encode_input(recipient),
            },
            badger.deployer,
        )

    exec_direct(
        badger.devMultisig,
        {
            "to": badger.rewardsEscrow,
            "data": badger.rewardsEscrow.transfer.encode_input(
                token, recipient, amount
            ),
        },
        badger.deployer,
    )
