from datetime import datetime, timezone, timedelta
from enum import Enum

import gql
from gql.transport.aiohttp import AIOHTTPTransport
from pycoingecko import CoinGeckoAPI

from helpers.token_utils import distribute_test_ether
import json
import os

import ape_safe
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
import warnings
import requests
import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.gnosis_safe import convert_to_test_mode, exec_direct, get_first_owner
from helpers.constants import MaxUint256
from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.gas_utils import gas_strategies

SUBGRAPH_URL_UNISWAP = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
SUBGRAPH_URL_SUSHISWAP = "https://api.thegraph.com/subgraphs/name/dmihal/sushiswap"

coingecko = CoinGeckoAPI()
console = Console()

gas_strategies.set_default(gas_strategies.rapid)


def test_main():
    main()


def Average(lst):
    return sum(lst) / len(lst)


def fetch_average_price(oracle_subgraph: gql.Client, pair_address: str, num_hours: int) -> float:
    start_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=num_hours - 1)
    query = f"""
    {{
      pairHourDatas(where: {{pair: "{pair_address.lower()}" hourStartUnix_gte: {int(start_time.timestamp())}}}) {{
        hourStartUnix
        reserve0
        reserve1
      }}
    }}"""
    print(query)

    data = [
        {
            "time": datetime.fromtimestamp(price_point['hourStartUnix'], tz=timezone.utc).
                strftime('%Y-%m-%d %H:%M:%S'),
            "digg": float(price_point["reserve0"]),
            'wbtc': float(price_point["reserve1"])
        }
        for price_point in oracle_subgraph.execute(gql.gql(query))["pairHourDatas"]
    ]
    for price_point in data:
        price_point["digg/wbtc"] = price_point["digg"] / price_point["wbtc"]
    console.log(data)

    return sum(price_point["digg/wbtc"] for price_point in data) / len(data)


def main():
    """
    Connect to badger system, and configure multisig for running transactions in local fork without access to accounts
    """

    # Connect badger system from file
    badger = connect_badger()
    digg = badger.digg

    sushi = SushiswapSystem()
    sushiPair = sushi.getPair(digg.token, registry.tokens.wbtc)

    uni = UniswapSystem()
    uniPair = uni.getPair(digg.token, registry.tokens.wbtc)

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    if rpc.is_active():
        distribute_test_ether(badger.devMultisig, Wei("5 ether"))

    # Multisig wrapper

    # Get price data from sushiswap, uniswap, and coingecko

    coingecko_prices = coingecko.get_price(ids=["digg", "bitcoin"], vs_currencies="usd")
    digg_usd_coingecko = coingecko_prices["digg"]["usd"]
    btc_usd_coingecko = coingecko_prices["bitcoin"]["usd"]
    digg_btc_coingecko = digg_usd_coingecko / btc_usd_coingecko

    oracle_uniswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_UNISWAP),
        fetch_schema_from_transport=True
    )
    oracle_sushiswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_SUSHISWAP),
        fetch_schema_from_transport=True
    )
    uniTWAP = fetch_average_price(oracle_uniswap, uniPair.address, 24)
    sushiTWAP = fetch_average_price(oracle_sushiswap, sushiPair.address, 24)
    averageTWAP = (uniTWAP + sushiTWAP) / 2

    console.print({
        "uniTWAP": uniTWAP,
        "sushiTWAP": sushiTWAP,
        "averageTWAP": averageTWAP,
        "digg_btc_coingecko": digg_btc_coingecko
    })

    supplyBefore = digg.token.totalSupply()

    print("spfBefore", digg.token._sharesPerFragment())
    print("supplyBefore", digg.token.totalSupply())

    marketValue = Wei(str(averageTWAP) + " ether")

    print(marketValue)

    print(int(marketValue * 10 ** 18))

    print("digg_btc_coingecko", digg_btc_coingecko, averageTWAP, marketValue)

    if rpc.is_active():
        distribute_test_ether(digg.centralizedOracle, Wei("5 ether"))

    centralizedMulti = GnosisSafe(digg.centralizedOracle)

    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 0))
    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 1))

    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 0))
    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 1))

    print(digg.cpiMedianOracle.getData.call())

    print("pair before", sushiPair.getReserves())
    print("uniPair before", uniPair.getReserves())

    tx = centralizedMulti.execute(
        MultisigTxMetadata(description="Set Market Data"),
        {
            "to": digg.marketMedianOracle.address,
            "data": digg.marketMedianOracle.pushReport.encode_input(marketValue),
        },
    )
    chain.mine()

    print(tx.call_trace())
    print(tx.events)

    chain.sleep(hours(0.4))
    chain.mine()

    in_rebase_window = digg.uFragmentsPolicy.inRebaseWindow()

    while not in_rebase_window:
        print("Not in rebase window...")
        chain.sleep(hours(0.1))
        chain.mine()
        in_rebase_window = digg.uFragmentsPolicy.inRebaseWindow()

    tx = digg.orchestrator.rebase({'from': accounts[0]})
    chain.mine()

    supplyAfter = digg.token.totalSupply()

    print("spfAfter", digg.token._sharesPerFragment())
    print("supplyAfter", supplyAfter)
    print("supplyChange", supplyAfter / supplyBefore)
    print("supplyChangeOtherWay", supplyBefore / supplyAfter)

    print("pair after", sushiPair.getReserves())
    print("uniPair after", uniPair.getReserves())

    # Make sure sync() was called on the pools from call trace or events

    # Call Sync manually as deployer

