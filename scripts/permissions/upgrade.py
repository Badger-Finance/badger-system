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

def upgrade_contract(badger, helper, proxy, new_logic):
    testAdmin = helper.contract_from_abi(badger.testProxyAdmin.address, "IProxyAdmin", interface.IProxyAdmin.abi)
    console.print(f"Updating Proxy at {proxy} to logic {new_logic}")
    testAdmin.upgrade(proxy, new_logic)

def main():
    """
    Promote an experimental vault to official status
    """
    badger = connect_badger(load_deployer=True)

    if rpc.is_active():
        safe = ApeSafe(badger.testMultisig.address)
        helper = ApeSafeHelper(badger, safe)
        assert True
    else:
        from helpers.gas_utils import gas_strategies

        gas_strategies.set_default(gas_strategies.exponentialScalingFast)

    upgrade_contract(badger, helper, "0x8751d4196027d4e6da63716fa7786b5174f04c15", "0xBa814B22aE5aE2C063B4419a27df6389F8F5AB20")

    helper.publish()