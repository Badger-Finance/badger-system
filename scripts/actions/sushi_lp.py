from ape_safe import ApeSafe
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from rich import pretty
from rich.console import Console
from scripts.actions.helpers.GeyserDistributor import GeyserDistributor
from scripts.actions.helpers.StakingRewardsDistributor import StakingRewardsDistributor
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.sushiswap_system import SushiswapSystem
from tabulate import tabulate

from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth
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
from helpers.token_utils import get_token_balances
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    to_digg_shares,
    tx_wait,
    val,
)

console = Console()


def main():
    badger = connect_badger("deploy-final.json")
    digg = badger.digg

    tx_data = {
        "to": "0x8D29bE29923b68abfDD21e541b9374737B49cdAD",
        "data": "0x8d80ff0a000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000009fe00b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024694e80c300000000000000000000000000000000000000000000000000000000000000010019d099670a21bc0a8211a89b84cedf59abb4377f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000064beabacc80000000000000000000000003472a5a71965499acd81997a54bba8d852c6e53d000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000017c5d213c7a8f712f400019d099670a21bc0a8211a89b84cedf59abb4377f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000064beabacc8000000000000000000000000798d1be841a82a273720ce31c822c61a67a601c3000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000000000000001b69e2595003472a5a71965499acd81997a54bba8d852c6e53d00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f000000000000000000000000000000000000000000000068bce40cf18444c28000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001244a25d94a000000000000000000000000000000000000000000000002b01ee2a20a8a2a90000000000000000000000000000000000000000000000068bce40cf18444c28000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000000000000000604be4d100000000000000000000000000000000000000000000000000000000000000030000000000000000000000003472a5a71965499acd81997a54bba8d852c6e53d0000000000000000000000002260fac5e5542a773aa44fbcfedf7c193bc2c599000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2003472a5a71965499acd81997a54bba8d852c6e53d00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b300000000000000000000000019d97d8fa813ee2f51ad4b4e04ea08baf4dffc28000000000000000000000000000000000000000000000113a03d2f890b2c6cc00019d97d8fa813ee2f51ad4b4e04ea08baf4dffc2800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024b6b55f25000000000000000000000000000000000000000000000113a03d2f890b2c6cc000798d1be841a82a273720ce31c822c61a67a601c300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b30000000000000000000000007e7e112a68d8d2e221e11047a72ffc1065c38e1a00000000000000000000000000000000000000000000000000000001b69e2595007e7e112a68d8d2e221e11047a72ffc1065c38e1a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000246c361865000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e77007e7e112a68d8d2e221e11047a72ffc1065c38e1a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024b6b55f2500000000000000000000000000000000000000000000000000000001b69e25950019d97d8fa813ee2f51ad4b4e04ea08baf4dffc2800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f0000000000000000000000000000000000000000000000e203f5dc3c00323a8000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f00000000000000000000000000000000000000000000000777723ca5ab7fcb9000000000000000000000000000000000000000000000000000000000000000c4f305d71900000000000000000000000019d97d8fa813ee2f51ad4b4e04ea08baf4dffc280000000000000000000000000000000000000000000000e203f5dc3c00323a800000000000000000000000000000000000000000000000e203f5dc3c00323a8000000000000000000000000000000000000000000000000777723ca5ab7fcb90000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000000000000000604be4db007e7e112a68d8d2e221e11047a72ffc1065c38e1a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f00000000000000000000000000000000000000000000000048ada1feff60844a00d9e1ce17f2641f24ae83637ab66a2cca9c378b9f00000000000000000000000000000000000000000000000777723ca5ab7fcb9000000000000000000000000000000000000000000000000000000000000000c4f305d7190000000000000000000000007e7e112a68d8d2e221e11047a72ffc1065c38e1a00000000000000000000000000000000000000000000000048ada1feff60844a00000000000000000000000000000000000000000000000048ada1feff60844a00000000000000000000000000000000000000000000000777723ca5ab7fcb90000000000000000000000000b65cef03b9b89f99517643226d76e286ee999e7700000000000000000000000000000000000000000000000000000000604be4dd0000",
    }

    sushiBbadgerPair = "0x0a54d4b378c8dbfc7bc93be50c85debafdb87439"
    sushiBDiggPair = "0xf9440fedc72a0b8030861dcdac39a75b544e7a3c"

    sushiswap = SushiswapSystem()

    pair = interface.IUniswapV2Pair(sushiBbadgerPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    pair = interface.IUniswapV2Pair(sushiBDiggPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    usd_amount = 500000

    weth = interface.IERC20(registry.tokens.weth)

    console.log("..Before Safe")

    safe = ApeSafe(badger.devMultisig.address)
    ops_safe = ApeSafe(badger.opsMultisig.address)

    console.log("..After Safe Setup")

    # multi = GnosisSafe(badger.devMultisig)

    # multi.execute(
    #     MultisigTxMetadata(description="Run TX"),
    #     {"to": tx_data["to"], "data": tx_data["data"], "operation": 1},
    # )

    after = get_token_balances(
        [
            badger.token,
            digg.token,
            interface.IERC20(registry.tokens.usdc),
            interface.IERC20(sushiBbadgerPair),
            interface.IERC20(sushiBDiggPair),
        ],
        [badger.devMultisig],
    )
    after.print()

    pair = interface.IUniswapV2Pair(sushiBbadgerPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    pair = interface.IUniswapV2Pair(sushiBDiggPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    router = safe.contract(sushiswap.router.address)
    rewardsEscrow = safe.contract(badger.rewardsEscrow.address)
    badgerToken = safe.contract(badger.token.address)
    diggToken = safe.contract(digg.token.address)

    digg_to_lp = Wei("8.4 gwei")

    usd_per_side = 250000

    # TODO: Use banteg's nice value calc script.

    badger_usd = fetch_usd_price(badger.token.address)
    digg_usd = fetch_usd_price(digg.token.address)
    eth_usd = fetch_usd_price_eth()

    console.log(eth_usd)

    badger_to_swap = Wei(str(95000 / badger_usd) + " ether")
    badger_to_lp = Wei(str(usd_per_side / badger_usd) + " ether")
    digg_to_lp = Wei(str(usd_per_side / digg_usd) + " gwei")
    eth_out = Wei(str(usd_per_side / eth_usd) + " ether")

    console.print(
        {
            "badger_to_swap": badger_to_swap,
            "badger_to_lp": badger_to_lp,
            "digg_to_lp": digg_to_lp,
            "eth_out": eth_out,
            "badger_usd": badger_usd,
            "digg_usd": digg_usd,
            "eth_usd": eth_usd,
        }
    )

    badger_to_get_from_escrow = badger_to_swap + badger_to_lp

    # Get 250k worth of bBadger + $90k Amount to swap to ETH
    rewardsEscrow.transfer(badger.token, badger.devMultisig, badger_to_get_from_escrow)

    # Get 250k worth of bDigg
    rewardsEscrow.transfer(digg.token, badger.devMultisig, digg_to_lp)

    # Sell badger for 90k USD
    exact_eth = Wei(str(90000 / eth_usd) + " ether")

    console.print("exact_eth", exact_eth)

    assert badger.token.balanceOf(badger.devMultisig) >= badger_to_swap

    print("a")

    badgerToken.approve(sushiswap.router.address, badger_to_swap)

    print("b")

    assert (
        badger.token.allowance(badger.devMultisig, sushiswap.router.address)
        == badger_to_swap
    )

    router.swapTokensForExactETH(
        exact_eth,
        int(badger_to_swap * 1.02),
        [badger.token, registry.tokens.wbtc, registry.tokens.weth],
        badger.devMultisig,
        chain.time() + 200000,
    )

    print("d")

    after = get_token_balances([badger.token, digg.token], [badger.devMultisig])
    after.print()

    # Deposit Badger for bBadger
    # Deposit DIGG for bDigg

    bBadger_address = badger.getSett("native.badger").address
    bDigg_address = badger.getSett("native.digg").address

    console.print(bBadger_address, bDigg_address)

    abi = Sett.abi

    bBadger = safe.contract_from_abi(bBadger_address, "Sett", abi)
    bDigg = safe.contract_from_abi(bDigg_address, "Sett", abi)

    badgerToken.approve(bBadger.address, badger_to_lp)

    print(bBadger)
    console.print(bBadger)
    bBadger.deposit(badger_to_lp)

    diggToken.approve(bDigg.address, digg_to_lp)
    bDigg.approveContractAccess(badger.devMultisig)

    tx = bDigg.deposit(digg_to_lp)
    console.print(tx.events)

    # tx = bDigg.withdraw(bDigg.balanceOf(badger.devMultisig))
    # console.print(tx.events)

    after = get_token_balances(
        [
            badger.token,
            digg.token,
            interface.IERC20(bDigg.address),
            interface.IERC20(bBadger.address),
        ],
        [badger.devMultisig],
    )
    after.print()

    # Seed pools: 250k worth of bToken, 250k worth of ETH

    tokenA = bBadger

    amountA = (badger_to_lp * 10 ** 18) / bBadger.getPricePerFullShare()
    amountB = eth_out

    # TODO: Set the amount of ETH to what is required.

    after = get_token_balances(
        [
            badger.token,
            digg.token,
            interface.IERC20(bDigg.address),
            interface.IERC20(bBadger.address),
            interface.IERC20(sushiBbadgerPair),
            interface.IERC20(sushiBDiggPair),
        ],
        [badger.devMultisig],
    )
    after.print()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)

    """
    How do we get exactly 250k worth of each asset?
    Calculate how much you need to get 250k

    ===== Normal Assets =====
    250k / USD price of asset 

    ===== For bTokens =====
    How much original token to get: 250k / USD price of underlying asset 
    bToken will handle itself
    """

    tokenA.approve(sushiswap.router, amountA)
    console.print(
        "addLiquidityETH",
        {
            "tokenA": tokenA.address,
            "amountA": amountA,
            "amountB": amountB,
            "badger ppfs": bBadger.getPricePerFullShare(),
            "original supply": Wei("4000 gwei"),
            "current supply": digg.token.totalSupply(),
        },
    )

    router.addLiquidityETH(
        tokenA.address,
        amountA,
        int(amountA * 0.95),
        int(eth_out * 0.95),
        badger.devMultisig,
        chain.time() + 200000,
        {"value": eth_out},
    )

    tokenA = bDigg

    amountA = ((digg_to_lp * 10 ** 9) * 10 ** 18) / bDigg.getPricePerFullShare()
    amountA = amountA * (Wei("4000 gwei")) / digg.token.totalSupply()

    print("expected bDigg", amountA)

    amountA = bDigg.balanceOf(badger.devMultisig)

    print("actual bDigg", amountA)

    tokenA.approve(sushiswap.router, amountA)
    console.print(
        "addLiquidityETH",
        {
            "tokenA": tokenA.address,
            "amountA": amountA,
            "amountB": amountB,
            "digg ppfs": bDigg.getPricePerFullShare(),
        },
    )

    router.addLiquidityETH(
        tokenA.address,
        amountA,
        int(amountA * 0.95),
        int(eth_out * 0.95),
        badger.devMultisig,
        chain.time() + 200000,
        {"value": eth_out},
    )

    after = get_token_balances(
        [
            badger.token,
            digg.token,
            interface.IERC20(bDigg.address),
            interface.IERC20(bBadger.address),
            interface.IERC20(sushiBbadgerPair),
            interface.IERC20(sushiBDiggPair),
        ],
        [badger.devMultisig],
    )
    after.print()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)

    pair = interface.IUniswapV2Pair(sushiBbadgerPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    pair = interface.IUniswapV2Pair(sushiBDiggPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    safe.post_transaction(safe_tx)

    pair = interface.IUniswapV2Pair(sushiBbadgerPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )

    pair = interface.IUniswapV2Pair(sushiBDiggPair)
    console.print(
        {
            "getReserves": pair.getReserves(),
            "token0": pair.token0(),
            "token1": pair.token1(),
            "price0CumulativeLast": pair.price0CumulativeLast(),
            "price1CumulativeLast": pair.price1CumulativeLast(),
        }
    )
