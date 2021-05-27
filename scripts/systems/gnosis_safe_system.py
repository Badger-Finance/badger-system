from brownie import *
from helpers.constants import AddressZero
from helpers.registry import registry, artifacts
from dotmap import DotMap


def connect_gnosis_safe(address):
    return Contract.from_abi(
        "GnosisSafe",
        address,
        artifacts.gnosis_safe.GnosisSafe["abi"],
    )


class GnosisSafeSystem:
    def __init__(self):
        self.masterCopy = Contract.from_abi(
            "GnosisSafe",
            web3.toChecksumAddress(registry.gnosis_safe.addresses.masterCopy),
            registry.gnosis_safe.artifacts.GnosisSafe["abi"],
        )

        self.proxyFactory = Contract.from_abi(
            "ProxyFactory",
            web3.toChecksumAddress(registry.gnosis_safe.addresses.proxyFactory),
            artifacts.gnosis_safe.ProxyFactory["abi"],
        )

    def deployGnosisSafe(self, params, signer):
        encodedParams = self.masterCopy.setup.encode_input(
            params.owners,
            params.threshold,
            params.to,
            params.data,
            params.fallbackHandler,
            params.paymentToken,
            params.payment,
            params.paymentReceiver,
        )

        tx = self.proxyFactory.createProxy(
            self.masterCopy, encodedParams, {"from": signer}
        )

        return Contract.from_abi(
            "GnosisSafe",
            tx.events["ProxyCreation"][0]["proxy"],
            registry.gnosis_safe.artifacts.GnosisSafe["abi"],
        )
