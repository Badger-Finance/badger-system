import random
from rich.console import Console
from typing import (
    Optional,
    List,
    Any,
)
from brownie import (
    reverts,
    accounts,
    network,
    RemoteDefenderUpgradeable,
    ThirdPartyContractAccess,
)

from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger

console = Console()

# Schema: (METHOD_NAME, (*ARGS),)
SETT_METHODS_AND_ARGS = [
    ("depositAll", (),),
    ("withdrawAll", (),),
    ("withdraw", (0,),),
    ("deposit", (0,),),
]


def test_defender():
    # connect to prod deploy and run simulation
    badger = connect_badger(badger_config.prod_json)
    badger.upgrade.upgrade_sett_contracts()

    badger.deploy_logic("RemoteDefenderUpgradeable", RemoteDefenderUpgradeable)
    badger.deploy_defender()
    badger.configureDefender()

    deployer = badger.deployer
    defender = badger.defender

    # Test EOA access.
    user = accounts[random.randint(10, 40)]

    # Validate the access unrestricted case works first.
    for sett in badger.sett_system.vaults.values():
        _testSett(user, sett)

    defender.pauseGlobal({"from": deployer})
    for sett in badger.sett_system.vaults.values():
        _testSett(user, sett, error="Pausable: paused")
    defender.unpauseGlobal({"from": deployer})

    defender.freeze(user, {"from": deployer})
    for sett in badger.sett_system.vaults.values():
        _testSett(user, sett, error="Caller frozen")
    defender.unfreeze(user, {"from": deployer})

    # Validate the access unrestricted case works last.
    for sett in badger.sett_system.vaults.values():
        _testSett(user, sett)

    # Test non EOA access.
    for sett in badger.sett_system.vaults.values():
        contract = ThirdPartyContractAccess.deploy(sett, {"from": deployer})
        _testSett(user, contract, error="Access denied for caller")

        # Approve third party contract for access.
        defender.approve(contract, {"from": deployer})
        _testSett(user, contract)

        # Revoke access.
        defender.revoke(contract, {"from": deployer})
        _testSett(user, contract, error="Access denied for caller")


def _testSett(
    user: network.account.Account,
    sett: network.contract.ProjectContract,
    error: Optional[str] = None,
) -> None:
    for (method, args) in SETT_METHODS_AND_ARGS:
        _testContractMethod(
            sett,
            method,
            args + ({"from": user},),
            error=error
        )


def _testContractMethod(
    contract: network.contract.ProjectContract,
    method: str,
    args: List[Any],
    error: Optional[str] = None,
) -> None:
    if error is None:
        getattr(contract, method)(*args)
        return

    with reverts(error):
        getattr(contract, method)(*args)
