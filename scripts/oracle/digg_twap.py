from datetime import datetime, timezone
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

cg = CoinGeckoAPI()
console = Console()

SUBGRAPH_URL_UNISWAP = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
SUBGRAPH_URL_SUSHISWAP = "https://api.thegraph.com/subgraphs/name/dmihal/sushiswap"
# WBTC-DIGG pair addresses
PAIR_ADDRESS_UNISWAP = "0xe86204c4eddd2f70ee00ead6805f917671f56c52"
PAIR_ADDRESS_SUSHISWAP = "0x9a13867048e01c663ce8ce2fe0cdae69ff9f35e3"


def test_main():
    main()


def fetch_average_price(oracle_subgraph: gql.Client, pair_address: str, num_hours: int) -> float:
    start_time = int(datetime.now(timezone.utc).timestamp()) - hours(num_hours + 2)
    query = gql.gql(f"""
    {{
      pairHourDatas(where: {{pair: "{pair_address}" hourStartUnix_gte: {start_time}}}) {{
        id
        hourStartUnix
        reserve0
        reserve1
        reserveUSD
      }}
    }}
    """)
    data = oracle_subgraph.execute(query)["pairHourDatas"][-num_hours:]
    # console.log(data)
    return sum(float(price_point["reserve0"]) / float(price_point["reserve1"]) for price_point in data) / num_hours


def main():
    """
    Connect to badger system, and configure multisig for running transactions in local fork without access to accounts
    """

    # Connect badger system from file
    badger = connect_badger("deploy-final.json")
    digg = connect_digg("deploy-final.json")

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    # Multisig wrapper
    multi = GnosisSafe(badger.devMultisig, testMode=True)

    # Get price data from sushiswap, uniswap, and coingecko

    digg_per_btc = cg.get_price(ids="digg", vs_currencies="btc")["digg"]["btc"]

    oracle_uniswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_UNISWAP),
        fetch_schema_from_transport=True
    )
    oracle_sushiswap = gql.Client(
        transport=AIOHTTPTransport(url=SUBGRAPH_URL_SUSHISWAP),
        fetch_schema_from_transport=True
    )
    twap_uniswap = fetch_average_price(oracle_uniswap, PAIR_ADDRESS_UNISWAP, 24)
    twap_sushiswap = fetch_average_price(oracle_sushiswap, PAIR_ADDRESS_SUSHISWAP, 24)
    twap = (twap_uniswap + twap_sushiswap) / 2
    print(f'twap_uniswap = {twap_uniswap}\ntwap_sushiswap = {twap_sushiswap}\naverage = {twap}\n')

    supply_before = digg.token.totalSupply()

    print("spfBefore", digg.token._sharesPerFragment())
    print("supply_before", digg.token.totalSupply())

    marketValue = Wei(str(twap) + " ether")

    print(marketValue)

    print(int(marketValue * 10 ** 18))

    print("digg_per_btc", digg_per_btc, twap, marketValue)

    centralizedMulti = GnosisSafe(digg.centralizedOracle)
    
    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 0))
    print(digg.marketMedianOracle.providerReports(digg.centralizedOracle, 1))

    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 0))
    print(digg.cpiMedianOracle.providerReports(digg.constantOracle, 1))

    print(digg.cpiMedianOracle.getData.call())

    sushi = SushiswapSystem()
    pair = sushi.getPair(digg.token, registry.tokens.wbtc)

    uni = UniswapSystem()
    uniPair = uni.getPair(digg.token, registry.tokens.wbtc)

    print("pair before", pair.getReserves())
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

    chain.sleep(hours(1.8))
    chain.mine()

    tx = digg.orchestrator.rebase({'from': badger.deployer})
    chain.mine()

    supplyAfter = digg.token.totalSupply()

    print("spfAfter", digg.token._sharesPerFragment())
    print("supplyAfter", supplyAfter)
    print("supplyChange", supplyAfter / supply_before)
    print("supplyChangeOtherWay", supply_before / supplyAfter )

    print("pair after", pair.getReserves())
    print("uniPair after", uniPair.getReserves())

    # Make sure sync() was called on the pools from call trace or events

    # Call Sync manually as deployer

