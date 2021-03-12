from brownie import *
from rich.console import Console
import math
console = Console()

MAX_DIGG_ALLOC = 1.0
MIN_DIGG_ALLOC = 0.3
MAX_DIGG_THRESHOLD = 0.8
MIN_DIGG_THRESHOLD = 1.3
EQULIBRIUM = 0.5
TARGET = 1.0

def main():
    diggBTCPriceFeed = Contract.from_explorer("0xe49ca29a3ad94713fc14f065125e74906a6503bb")
    latestData = diggBTCPriceFeed.latestRoundData()
    ratio = latestData[1]/1e8
    calculateDiggAllocation(ratio)
    for index in range(50,175,5):
        calculateDiggAllocation(round(index/100,2))


def calculateDiggAllocation(ratio):
    if ratio >= 1.0:
        console.log("Digg above peg")
        diggSettAllocation = max(MIN_DIGG_ALLOC,
        MIN_DIGG_ALLOC + (MIN_DIGG_THRESHOLD - ratio) * ((EQULIBRIUM - MIN_DIGG_ALLOC)/(MIN_DIGG_THRESHOLD - TARGET))
        )
    elif ratio < 1.0:
        console.log("DIGG below peg")
        diggSettAllocation = min(MAX_DIGG_ALLOC,
        EQULIBRIUM + (TARGET - ratio) * ((MAX_DIGG_ALLOC - EQULIBRIUM)/(TARGET - MAX_DIGG_THRESHOLD))
        )
    console.log( "Ratio:{}%".format( round (ratio * 100 ), 2 ) )

    console.log( "Digg sett allocation {}%,Badger setts allocation {}%".format(round((diggSettAllocation * 100),2), round(  (1 - diggSettAllocation)*100,2)))