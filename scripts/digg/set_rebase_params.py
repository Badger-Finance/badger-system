from helpers.token_utils import distribute_test_ether
from brownie.project.main import new
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from dotmap import DotMap
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.time_utils import days, hours
import os
import json
from scripts.systems.badger_system import BadgerSystem, connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from config.badger_config import badger_config
from helpers.gas_utils import gas_strategies
from helpers.console_utils import console


def main():
    badger = connect_badger(badger_config.prod_json)
    deployer = badger.deployer

    multi = GnosisSafe(badger.devMultisig)
    rebaseParams = {}
    rebaseParams[
        "minRebaseTimeIntervalSec"
    ] = badger.digg.uFragmentsPolicy.minRebaseTimeIntervalSec()
    rebaseParams[
        "rebaseWindowOffsetSec"
    ] = badger.digg.uFragmentsPolicy.rebaseWindowOffsetSec()
    rebaseParams[
        "rebaseWindowLengthSec"
    ] = badger.digg.uFragmentsPolicy.rebaseWindowLengthSec()

    console.print(rebaseParams)

    newWindowLength = hours(6)

    console.print(newWindowLength)

    multi.execute(
        MultisigTxMetadata(description="Set Rebase Params"),
        {
            "to": badger.digg.uFragmentsPolicy.address,
            "data": badger.digg.uFragmentsPolicy.setRebaseTimingParameters.encode_input(
                rebaseParams["minRebaseTimeIntervalSec"],
                rebaseParams["rebaseWindowOffsetSec"],
                newWindowLength,
            ),
        },
    )

    chain.mine()

    tx = badger.digg.orchestrator.rebase({"from": badger.deployer})
    print(tx.call_trace())

    tx = badger.digg.orchestrator.rebase({"from": badger.deployer})
    print(tx.call_trace())
