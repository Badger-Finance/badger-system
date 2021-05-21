from brownie import *
from rich.console import Console
from statistics import mean

diggBTCOracleContract = "0xe49ca29a3ad94713fc14f065125e74906a6503bb"
console = Console()

MAX_DIGG_ALLOC = 1.0
MIN_DIGG_ALLOC = 0.3
MAX_DIGG_THRESHOLD = 0.7
MIN_DIGG_THRESHOLD = 1.3
EQULIBRIUM = 0.5
TARGET = 1.0


def digg_btc_twap(start, end):
    startTimestamp = web3.eth.getBlock(start)["timestamp"]
    endTimestamp = web3.eth.getBlock(end)["timestamp"]
    diggBTCOracle = Contract.from_explorer(diggBTCOracleContract)
    latestRound = diggBTCOracle.latestRound()
    ratios = []
    currentTimestamp = endTimestamp
    while currentTimestamp > startTimestamp:
        roundData = diggBTCOracle.getRoundData(latestRound)
        ratios.append(roundData[1] / 1e8)
        currentTimestamp = roundData[3]
        latestRound = latestRound - 1
    return mean(ratios)


def calculate_digg_allocation(ratio):
    if ratio >= 1.0:
        console.log("Digg above peg")
        diggSettAllocation = max(
            MIN_DIGG_ALLOC,
            MIN_DIGG_ALLOC
            + (MIN_DIGG_THRESHOLD - ratio)
            * ((EQULIBRIUM - MIN_DIGG_ALLOC) / (MIN_DIGG_THRESHOLD - TARGET)),
        )
    elif ratio < 1.0:
        console.log("DIGG below peg")
        diggSettAllocation = min(
            MAX_DIGG_ALLOC,
            EQULIBRIUM
            + (TARGET - ratio)
            * ((MAX_DIGG_ALLOC - EQULIBRIUM) / (TARGET - MAX_DIGG_THRESHOLD)),
        )
    console.log(
        "Ratio :{} \nDiggSettAllocation :{} \nBadgerSettAllocation:{} ".format(
            ratio, diggSettAllocation, 1 - diggSettAllocation
        )
    )
    return diggSettAllocation
