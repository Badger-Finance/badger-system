from enum import Enum

from brownie import *
from rich.console import Console
from tabulate import tabulate

console = Console()

"""
Gnosis safe helpers

Encode, track signatures, and execute transactions for a Gnosis safe.
On test networks leveraging Ganache --unlock, take control of a Gnosis safe without ownership of corresponding accounts by:
    - Setting threshold to 1
    - Leveraging approved hash voting
"""


class OPERATION(Enum):
    CREATE = 0
    CALL = 2


class GnosisSafe:
    def __init__(self, contract, testMode=True):
        self.contract = contract
        self.firstOwner = get_first_owner(contract)
        self.transactions = {}
        self.testMode = testMode

        if testMode:
            self.convert_to_test_mode()

    # Must be on Ganache instance and Gnosis safe must be --unlocked

    def convert_to_test_mode(self):
        self.contract.changeThreshold(1, {"from": self.contract.address})
        assert self.contract.getThreshold() == 1

    def execute(self, params, signer=None):
        return exec_direct(self.contract, params, signer)

    def addTx(self, key, params):
        self.transactions[key] = params

    def executeTx(self, key):

        self.printTx(key)

        if self.testMode:
            return exec_direct(self.contract, self.transactions[key])

    def printTx(self, key):
        params = self.transactions[key]

        console.print("\n[red]== 🦡 Execute: {} 🦡 ==[/red]".format(key))
        table = []

        table.append([key, params["to"], params["data"]])

        print(tabulate(table, headers=["key", "to", "data",], tablefmt="rst",))


def multisig_success(tx):
    if len(tx.events["ExecutionSuccess"]) > 0:
        return True

    if len(tx.events["ExecutionFailure"]) > 0:
        return False

    else:
        return False


# Must be on Ganache instance and Gnosis safe must be --unlocked
def convert_to_test_mode(contract):
    contract.changeThreshold(1, {"from": contract.address})
    assert contract.getThreshold() == 1


def generate_approve_hash_signature(signer):
    print("address", signer.address, signer.address[2 : len(signer.address)])
    # padded address + 32 empty bytes + 01 (sig type)
    return (
        "0x"
        + "000000000000000000000000"
        + signer.address[2 : len(signer.address)]
        + "0000000000000000000000000000000000000000000000000000000000000000"
        + "01"
    )


def exec_transaction(contract, params, signer):
    # Set default parameters
    if not "value" in params.keys():
        params["value"] = 0

    if not "operation" in params.keys():
        params["operation"] = 0

    params["safeTxGas"] = 2000000
    params["baseGas"] = 2000000
    params["gasPrice"] = Wei("0.1 ether")
    params["gasToken"] = "0x0000000000000000000000000000000000000000"
    params["refundReceiver"] = signer.address
    params["return"] = signer.address

    # print("exec_direct", contract, color.pretty_dict(params), signer)

    tx = contract.execTransaction(
        params["to"],
        params["value"],
        params["data"],
        params["operation"],
        params["safeTxGas"],
        params["baseGas"],
        params["gasPrice"],
        params["gasToken"],
        params["refundReceiver"],
        params["signatures"],
        {"from": signer, "gas_limit": 6000000},
    )
    return tx


def get_first_owner(contract):
    return contract.getOwners()[0]


def exec_direct(contract, params, signer=None):
    signer = accounts.at(contract.getOwners()[0], force=True)
    params["signatures"] = generate_approve_hash_signature(signer)
    return exec_transaction(contract, params, signer)
