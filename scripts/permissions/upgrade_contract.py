from scripts.view.acl_viewer import print_access_control
from helpers.time_utils import days, to_utc_date
from ape_safe import ApeSafe
from brownie import *
from helpers.constants import *
from eth_abi import encode_abi
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper, GnosisSafe, MultisigTxMetadata
from config.badger_config import badger_config, digg_config, sett_config
from helpers.registry import artifacts
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from helpers.registry import registry
from tabulate import tabulate
from scripts.permissions.access_control import BadgerRewardsManagerHelper

def change_implementation(badger, helper, admin, proxy, new_implementation):
    admin = helper.contract_from_abi(admin.address, "ProxyAdmin", artifacts.open_zeppelin["ProxyAdmin"]["abi"])

    console.print(f"Change proxy admin of {proxy} to {new_implementation}")
    admin.upgrade(proxy, new_implementation)
    assert admin.getProxyImplementation(proxy) == new_implementation

def main():
    """
    Promote an experimental vault to official status
    """
    badger = connect_badger(load_deployer=True)

    if rpc.is_active():
        dev_multi = ApeSafe(badger.testMultisig.address)
        helper = ApeSafeHelper(badger, dev_multi)
        assert True
    else:
        from helpers.gas_utils import gas_strategies
        gas_strategies.set_default(gas_strategies.exponentialScalingFast)

    change_implementation(badger, helper, badger.testProxyAdmin, badger.keeperAccessControl ,"0xc8e7c6F20582239D80bff8e4dE08cA53A1C25A64")

    helper.publish()
