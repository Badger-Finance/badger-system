from enum import Enum

from ape_safe import ApeSafe
from helpers.token_utils import distribute_test_ether

from brownie import *
from rich.console import Console
from tabulate import tabulate
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.multicall import func

console = Console()

"""
Gnosis safe helpers

Encode, track signatures, and execute transactions for a Gnosis safe.
On test networks leveraging Ganache --unlock, take control of a Gnosis safe without ownership of corresponding accounts by:
    - Setting threshold to 1
    - Leveraging approved hash voting
"""


class ApeSafeHelper:
    def __init__(self, badger, safe: ApeSafe):
        self.badger = badger
        self.safe = safe

    def getSett(self, key):
        abi = Sett.abi
        return self.safe.contract_from_abi(
            self.badger.getSett(key).address, "Sett", abi
        )

    def getStrategy(self, key):
        # Get strategy name
        # abi = contract_name_to_artifact()
        # return self.safe.contract_from_abi(self.badger.getSett(key).address, "Strategy", abi)
        return True

    def publish(self):
        safe_tx = self.safe.multisend_from_receipts()
        self.safe.preview(safe_tx)
        data = self.safe.print_transaction(safe_tx)
        self.safe.post_transaction(safe_tx)

    def contract_from_abi(self, address, name, abi) -> Contract:
        """
        Instantiate a Brownie Contract owned by Safe account.
        """
        if not web3.isChecksumAddress(address):
            address = web3.ens.resolve(address)
        return Contract.from_abi(
            address=address, owner=self.safe.account, name=name, abi=abi
        )

    def print_transaction(self, safe_tx):
        safe_tx.safe_tx_gas = 7000000
        safe_tx.base_gas = 8000000
        data = {
            "to": safe_tx.to,
            "value": safe_tx.value,
            "data": safe_tx.data.hex() if safe_tx.data else None,
            "operation": safe_tx.operation,
            "gasToken": safe_tx.gas_token,
            "safeTxGas": safe_tx.safe_tx_gas,
            "baseGas": safe_tx.base_gas,
            "gasPrice": safe_tx.gas_price,
            "refundReceiver": safe_tx.refund_receiver,
            "nonce": safe_tx.safe_nonce,
            "contractTransactionHash": safe_tx.safe_tx_hash.hex(),
            "signature": safe_tx.signatures.hex() if safe_tx.signatures else None,
            "origin": "github.com/banteg/ape-safe",
        }
        print(data)
        return data


class OPERATION(Enum):
    CREATE = 0
    CALL = 2


class MultiSend:
    def __init__(self, address):
        self.multisend = interface.IMultisend(address)


class MultisendTx:
    def __init__(self, call_type=0, to="", value=0, data=""):
        self.call_type = call_type
        self.to = to
        self.value = value
        self.data = data

        self.encoded = ""
        if self.call_type == 0:
            self.encoded += "00000000"
        elif self.call_type == 1:
            self.encoded += "00000001"
        """
        How to encode multisend TX:
        [call type] - 8 bits
        [to] - 256 bits address
        [value] - 256 bits hex number
        [data length] - 256 bits hex number
        [data] - arbitrary hex data [signature][params]
        """


class MultisendBuilder:
    def __init__(self):
        self.txs = []

    def add(self, tx: MultisendTx):
        self.txs.append(tx)
        """
        """


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
        return (
            "description: "
            + self.description
            + "\n"
            + "operation: "
            + str(self.operation)
            + "\n"
            + "callInfo: "
            + str(self.callInfo)
            + "\n"
        )


class MultisigTx:
    def __init__(self, params, metadata: MultisigTxMetadata):
        self.params = params
        self.metadata = metadata

    # def printMetadata(self):

    # def printParams(self):


class GnosisSafe:
    def __init__(self, contract, testMode=True):
        self.contract = connect_gnosis_safe(contract)

        console.print("contract", contract)
        self.firstOwner = get_first_owner(contract)
        self.transactions = []
        self.testMode = testMode

        if testMode and rpc.is_active():
            distribute_test_ether(self.firstOwner, Wei("2 ether"))
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

        print(
            tabulate(
                table,
                tablefmt="pretty",
            )
        )


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

    print(signer)
    if not "safeTxGas" in params.keys():
        params["safeTxGas"] = 4000000
    if not "baseGas" in params.keys():
        params["baseGas"] = 5000000
    if not "gasPrice" in params.keys():
        params["gasPrice"] = Wei("0.1 ether")
    if not "gasToken" in params.keys():
        params["gasToken"] = "0x0000000000000000000000000000000000000000"
    if not "refundReceiver" in params.keys():
        params["refundReceiver"] = signer.address
    if not "return" in params.keys():
        params["return"] = signer.address
    if not "nonce" in params.keys():
        params["nonce"] = contract.nonce()

    nonce = 2
    # print("exec_direct", contract, color.pretty_dict(params), signer)

    print(contract)

    encoded = contract.encodeTransactionData(
        params["to"],
        params["value"],
        params["data"],
        params["operation"],
        params["safeTxGas"],
        params["baseGas"],
        params["gasPrice"],
        params["gasToken"],
        params["refundReceiver"],
        nonce,
    )

    hash = contract.getTransactionHash(
        params["to"],
        params["value"],
        params["data"],
        params["operation"],
        params["safeTxGas"],
        params["baseGas"],
        params["gasPrice"],
        params["gasToken"],
        params["refundReceiver"],
        nonce,
    )

    console.log("Transaction Data", params)
    console.print("Encoded TX", encoded)
    console.print("Tx Hash", hash)

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
