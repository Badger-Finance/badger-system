from brownie.network.contract import ProjectContract

from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata


# try all the methods in priority order
VERSION_METHODS = [
    "version",
    "baseStrategyVersion",
]


# Upgrades versioned proxy contract's impl/logic contract if not latest version.
# Contracts must implement a version method above or they default to version 0.0.
def upgrade_versioned_proxy(
    badger,
    # upgradeable proxy contract
    proxy: ProjectContract,
    # latest logic contract
    logic: ProjectContract,
) -> None:
    # Do nothing if the proxy and logic contracts have the same version
    # or if the logic contract has an older version.
    proxyVersion = _get_version(proxy)
    logicVersion = _get_version(logic)
    if (
         proxyVersion == logicVersion or
        float(logicVersion) < float(proxyVersion)
    ):
        return

    multi = GnosisSafe(badger.devMultisig)

    multi.execute(
        MultisigTxMetadata(description="Upgrade versioned proxy contract with new logic version",),
        {
            "to": badger.devProxyAdmin.address,
            "data": badger.devProxyAdmin.upgrade.encode_input(
                proxy, logic
            ),
        },
    )


def _get_version(contract: ProjectContract) -> float:
    for method in VERSION_METHODS:
        version, ok = _try_get_version(contract, method)
        if ok:
            return version

    # NB: Prior to V1.1, Setts do not have a version function.
    return 0.0


def _try_get_version(contract: ProjectContract, method: str) -> (float, bool):
    try:
        return getattr(contract, method)(), True
    except Exception:
        return 0.0, False

