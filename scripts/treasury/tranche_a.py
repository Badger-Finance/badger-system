from enum import Enum
from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe

import requests
from brownie import Wei, accounts, interface, rpc
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper, GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem

console = Console()


def main():
    """
    AAVE
    Compoound
    y3Crv
    """

    badger = connect_badger()
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    # AAVE
    aave = registry.aave_system()
    tokens = registry.token_system()
    compound = registry.compound_system()
    usdc = tokens.erc20_by_key("usdc")
    dfd = tokens.erc20_by_key("dfd")
    ausdc = tokens.erc20_by_key("ausdc")
    cusdc = compound.ctoken("usdc")

    safe = ApeSafe(badger.devMultisig.address)

    # TODO: Track the balances of the tokens representing your position here: AAVE USDC (aUSDC), Compound USDC (cUSDC), y3Crv Vault Position (y3Crv)

    # TODO: Figure out the addresses of these derived tokens

    # TODO: Track the balances of all the appropriate contracts where the USDC ends up
    snap = BalanceSnapshotter(
        [usdc, ausdc, cusdc, dfd, badger.token],
        [
            badger.devMultisig,
            aave.lendingPool,
            cusdc,
            compound.comptroller,
            badger.badgerTree,
        ],
    )

    usdc_per_position = Wei("3237154580000 wei")  # szabo = 10^6
    round_1 = Wei("1000000 wei")
    round_2 = usdc_per_position - round_1

    print(round_1, round_2)
    lendingPool = safe.contract(aave.lendingPool.address)
    usdcToken = safe.contract(usdc.address)
    dfd = safe.contract(dfd.address)
    rewardsEscrow = safe.contract(badger.rewardsEscrow.address)
    comptroller = safe.contract(compound.comptroller.address)
    cusdc = safe.contract(cusdc.address)

    snap.snap()

    # Tree Tokens
    """
    Deposit badger from rewardsEscrow, and DFD from self. About 200k tokens.
    60k Badger
    200k DFD
    (We have plenty of DIGG)
    """
    # rewardsEscrow.transfer(badger.token, badger.badgerTree, Wei("50000 ether"))
    # dfd.transfer(badger.badgerTree, Wei("200000 ether"))

    # # AAVE Deposit Test
    # usdcToken.approve(aave.lendingPool, round_1)
    # lendingPool.deposit(usdc, round_1, badger.devMultisig, 0)

    # Compound Deposit Test
    """
    comptroller.enterMarkets([usdc])
    usdc.approve(cUSDC)
    cUSDC.mint(<usdc amount>)
    """

    # comptroller.enterMarkets([usdc])
    # usdcToken.approve(cusdc, round_1)
    # cusdc.redeem(round_1)
    # lendingPool.withdraw(usdc, round_1, badger.devMultisig)

    snap.snap()
    snap.diff_last_two()

    # AAVE Deposit Full
    usdcToken.approve(aave.lendingPool, round_2)
    lendingPool.deposit(usdc, round_2, badger.devMultisig, 0)

    # Compound Deposit Full
    usdcToken.approve(cusdc, round_2)
    cusdc.mint(round_2)

    snap.snap()
    snap.diff_last_two()

    helper = ApeSafeHelper(badger, safe)
    helper.publish()

    """
    y3Crv
    Stake in CRV (one asset only> What is the slippage here vs otherwise.)
    Approve
    Depsoit into Yearn vaukt
    """

    # Testing: Check balances and assert we have the aToken

    # TODO: Safety features. Call a custom contract balanceVerifier that verifies that the multisig owns the appropriate amount of coins from each platform
