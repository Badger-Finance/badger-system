from enum import Enum

from brownie import *
from rich.console import Console
from tabulate import tabulate
from helpers.multicall import func
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

class MultisigTxMetadata:
    def __init__(self, description, operation=None, callInfo=None):
        self.description = description
        self.operation = operation
        self.callInfo = callInfo

        if not operation:
            self.operation = ""
        
        if not callInfo:
            self.callInfo = ""

    def __str__(self):
        return "description: " + self.description + "\n" + 'operation: ' + str(self.operation) + "\n" + 'callInfo: ' + str(self.callInfo) + "\n"


class MultisigTx:
    def __init__(self, params, metadata: MultisigTxMetadata):
        self.params = params
        self.metadata = metadata
    
    # def printMetadata(self):

    # def printParams(self):

class GnosisSafe:
    def __init__(self, contract, testMode=True):
        self.contract = contract
        self.firstOwner = get_first_owner(contract)
        self.transactions = []
        self.testMode = testMode

        if testMode and rpc.is_active():
            self.convert_to_test_mode()

    # Must be on Ganache instance and Gnosis safe must be --unlocked

    def convert_to_test_mode(self):
        self.contract.changeThreshold(1, {"from": self.contract.address})
        assert self.contract.getThreshold() == 1

    def execute(self, metadata: MultisigTxMetadata, params, print_output=True):
        self.transactions.append(MultisigTx(params, metadata))
        id = len(self.transactions) - 1
        return self.executeTx(id)

    def addTx(self, metadata: MultisigTxMetadata, params):
        """
        Store a transaction in the safes' memory, return it's index
        """
        self.transactions.append(MultisigTx(params, metadata))
        return len(self.transactions) - 1

    def executeTx(self, id=None, print_output=True):
        tx = None
        if not id:
            tx = self.transactions[-1]
        else:
            tx = self.transactions[id]

        if print_output:
            self.printTx(id)

        if self.testMode:
            tx = exec_direct(self.contract, tx.params)
            if print_output:
                print(tx.call_trace())
            # try: 
            #     failEvents = tx.events['ExecutionFailure']
            #     if len(failEvents) > 0:
            #         print(tx.events)
            #         assert False
            # except EventLookupError:
            return tx
        

    def get_first_owner(self):
        return self.contract.getOwners()[0]

    def printTx(self, key):
        tx = self.transactions[key]
        params = tx.params
        metadata = tx.metadata

        # Print something different if we're on a test network or main network
        console.print("\n[cyan] Multisig Command: {} 🦡[/cyan]".format(key))

        table = []

        table.append([key, metadata, params["to"], params["data"]])

        print(tabulate(table, tablefmt="pretty",))


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

    params["safeTxGas"] = 3000000
    params["baseGas"] = 3000000
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
