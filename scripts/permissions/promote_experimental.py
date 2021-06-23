from ape_safe import ApeSafe
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.gas_utils import gas_strategies

gas_strategies.set_default(gas_strategies.exponentialScalingFast)


def main():
    """
    Promote an experimental vault to official status
    """

    key = "experimental.sushiIBbtcWbtc"

    badger = connect_badger()
    safe = ApeSafe(badger.devMultisig.address)
    ops = ApeSafe(badger.opsMultisig.address)

    experimental_controller = safe.contract(
        badger.getController("experimental").address
    )
    native_controller = ops.contract(badger.getController("native").address)

    # Set experimental strategist to ops multisig
    experimental_controller.setStrategist(badger.opsMultisig)

    # Move contract upgradability behind timelock
    admin = ops.contract(badger.opsProxyAdmin.address)
    sett = ops.contract(badger.getSett("experimental.sushiIBbtcWbtc").address)
    strategy = ops.contract(badger.getStrategy("experimental.sushiIBbtcWbtc").address)

    assert badger.getProxyAdmin(sett) == badger.opsProxyAdmin
    assert badger.getProxyAdmin(strategy) == badger.opsProxyAdmin

    admin.changeProxyAdmin(sett, badger.devProxyAdmin)
    admin.changeProxyAdmin(strategy, badger.devProxyAdmin)

    assert badger.devProxyAdmin.owner() == badger.governanceTimelock

    # Move Sett to native controller
    sett.setController(native_controller)
    native_controller.setVault(sett.token(), sett)
    native_controller.approveStrategy(sett.token(), strategy)
    native_controller.setStrategy(sett.token(), strategy)

    helper = ApeSafeHelper(badger, safe)
    helper.publish()
