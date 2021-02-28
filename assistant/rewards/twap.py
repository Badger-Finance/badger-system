from brownie import *
from rich.console import Console
from statistics import mean
diggBTCOracleContract = "0xe49ca29a3ad94713fc14f065125e74906a6503bb"
console = Console()

def digg_btc_twap(start,end):
    startTimestamp = web3.eth.getBlock(start)["timestamp"]
    endTimestamp = web3.eth.getBlock(end)["timestamp"]
    diggBTCOracle = Contract.from_explorer(diggBTCOracleContract)
    latestRound = diggBTCOracle.latestRound()
    ratios = []
    currentTimestamp = endTimestamp
    while currentTimestamp > startTimestamp:
        roundData = diggBTCOracle.getRoundData(latestRound)
        ratios.append(roundData[1]/1e8)
        currentTimestamp = roundData[3]
        latestRound = latestRound - 1
    #console.log(ratios)
    #console.log(mean(ratios))
    return mean(ratios)


    


