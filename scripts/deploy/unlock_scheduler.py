from helpers.proxy_utils import deploy_proxy
from brownie import interface
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from helpers.constants import MaxUint256
from helpers.token_utils import diff_token_balances, get_token_balances

console = Console()

keys = [
    "native.uniBadgerWbtc",
    "harvest.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.renCrv",
    "native.badger",
    "native.sushiBadgerWbtc",
    "native.sushiWbtcEth",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
]


def test_signal_token_lock(badger: BadgerSystem, locker):
    opsMulti = GnosisSafe(badger.opsMultisig)

    for key in keys:
        geyser = badger.getGeyser(key)
        print(key, geyser)

        opsMulti.execute(
            MultisigTxMetadata(description="Test signal token lock"),
            {
                "to": locker.address,
                "data": locker.signalTokenLocks.encode_input(
                    [
                        (geyser, badger.token, 1, 1, chain.time()),
                        (geyser, badger.digg.token, 2, 2, chain.time()),
                    ]
                ),
            },
        )

        print(geyser.getUnlockSchedulesFor(badger.token))
        print(geyser.getUnlockSchedulesFor(badger.digg.token))


def grant_token_locking_permission(badger: BadgerSystem, locker):
    multi = GnosisSafe(badger.devMultisig)

    for key in keys:
        geyser = badger.getGeyser(key)
        print(key, geyser)

        multi.execute(
            MultisigTxMetadata(
                description="Add Geyser permission for {} to {}".format(key, locker)
            ),
            {
                "to": geyser.address,
                "data": geyser.grantRole.encode_input(TOKEN_LOCKER_ROLE, locker),
            },
        )

        assert geyser.hasRole(TOKEN_LOCKER_ROLE, locker)


def main():
    """
    Connect to badger system, and configure multisig for running transactions in local fork without access to accounts
    """

    # Connect badger system from file
    badger = connect_badger("deploy-final.json")

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    # Multisig wrapper
    multi = GnosisSafe(badger.devMultisig)

    unlockLogic = UnlockScheduler.at("0xc63d8a22d18dd42a9de8343fd7c888bda3e7516d")

    print(
        unlockLogic.initialize.encode_input(
            badger.opsMultisig, badger.opsMultisig, badger.guardian, badger.opsMultisig
        )
    )

    # dep2 = accounts.load("badger-deployer-2")

    unlockProxy = UnlockScheduler.at("0x1AADc00011939499a4d263d657Dd74b0E1176cF9")

    # unlockProxy = deploy_proxy(
    #     "UnlockScheduler",
    #     UnlockScheduler.abi,
    #     unlockLogic.address,
    #     badger.opsProxyAdmin.address,
    #     unlockLogic.initialize.encode_input(
    #         badger.opsMultisig, badger.opsMultisig, badger.guardian, badger.opsMultisig
    #     ),
    #     dep2,
    # )

    assert badger.opsProxyAdmin.getProxyImplementation(unlockProxy) == unlockLogic

    grant_token_locking_permission(badger, unlockProxy)

    # Test run: Attempt to set unlock schedules
    test_signal_token_lock(badger, unlockProxy)
