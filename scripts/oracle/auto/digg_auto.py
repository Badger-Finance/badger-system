from brownie import *
from scripts.systems.badger_system import connect_badger
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.gas_utils import gas_strategies

gas_strategies.set_default(gas_strategies.exponentialScalingFast)

def main():
    """
    Ping the hardcoded Chainlink oracle contract to format & forward latest data to Digg MedianOracle.
    """
    badger = connect_badger()
    badger.deployer = accounts.load("badger-utility")

    oracle = interface.IChainlinkForwarder("")
    oracle.getThePrice({'from': badger.deployer})