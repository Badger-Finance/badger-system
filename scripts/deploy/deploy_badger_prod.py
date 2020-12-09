import time

from brownie import *
from helpers.time_utils import days
from scripts.deploy.deploy_badger import deploy_flow


def main():
    badger = deploy_flow(test=False, outputToFile=True, uniswap=False)
    time.sleep(days(1))
