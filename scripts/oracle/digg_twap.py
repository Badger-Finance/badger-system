from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import os

import gql
from gql.transport.aiohttp import AIOHTTPTransport

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
from pycoingecko import CoinGeckoAPI

coingecko = CoinGeckoAPI()
console = Console()

SUBGRAPH_URL_UNISWAP = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
SUBGRAPH_URL_SUSHISWAP = "https://api.thegraph.com/subgraphs/name/dmihal/sushiswap"


def test_main():
    main()


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
    badger = connect_badger("deploy-final.json")
    digg = connect_digg("deploy-final.json")

    uniswap = UniswapSystem()
    sushiswap = SushiswapSystem()

    token_pair_uni = uniswap.getPair(digg.token, registry.tokens.wbtc)
    token_pair_sushi = sushiswap.getPair(digg.token, registry.tokens.wbtc)

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    # Multisig wrapper
    multi = GnosisSafe(badger.devMultisig, testMode=True)

    # Get price data from sushiswap, uniswap, and coingecko

    digg_per_btc = coingecko.get_price(ids="digg", vs_currencies="btc")["digg"]["btc"]

    oracle_uniswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_UNISWAP),
        fetch_schema_from_transport=True
    )
    oracle_sushiswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_SUSHISWAP),
        fetch_schema_from_transport=True
    )
    twap_uniswap = fetch_average_price(oracle_uniswap, token_pair_uni.address, 24)
    twap_sushiswap = fetch_average_price(oracle_sushiswap, token_pair_sushi.address, 24)
    twap = (twap_uniswap + twap_sushiswap) / 2
    print(f'twap_uniswap = {twap_uniswap}\ntwap_sushiswap = {twap_sushiswap}\naverage = {twap}\n')

    supply_before = digg.token.totalSupply()

    print("spf before", digg.token._sharesPerFragment())
    print("supply before", digg.token.totalSupply())

    market_value = Wei(str(twap) + " ether")

    print(market_value)

    print(int(market_value * 10 ** 18))

    print("digg_per_btc", digg_per_btc, twap, market_value)

    centralized_multi = GnosisSafe(digg.centralizedOracle)

    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 0))
    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 1))

    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 0))
    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 1))

    print(digg.cpiMedianOracle.getData.call())

    print("sushi pair before", token_pair_sushi.getReserves())
    print("uni pair before", token_pair_uni.getReserves())

    tx = centralized_multi.execute(
        MultisigTxMetadata(description="Set Market Data"),
        {
            "to": digg.marketMedianOracle.address,
            "data": digg.marketMedianOracle.pushReport.encode_input(market_value),
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

    tx = digg.orchestrator.rebase({'from': badger.deployer})
    chain.mine()

    supply_after = digg.token.totalSupply()

    print("spf after", digg.token._sharesPerFragment())
    print("supply after", supply_after)
    print("supply change", supply_after / supply_before)
    print("supply change other way", supply_before / supply_after )

    print("sushi pair after", token_pair_sushi.getReserves())
    print("uni pair after", token_pair_uni.getReserves())

    # Make sure sync() was called on the pools from call trace or events

    # Call Sync manually as deployer
