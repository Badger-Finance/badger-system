from brownie import *
from brownie.utils import color
from enum import Enum
from helpers.registry import registry
from eth_account import Account

gas_price = web3.toWei("80", "gwei")

# Send transaction from deployer hack
def send_raw_tx(address, data):
    key = get_account()

    transaction = {
        "to": address,
        "value": 0,
        "gas": 2000000,
        "gasPrice": gas_price,
        "nonce": web3.eth.getTransactionCount(
            "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b"
        ),
        "chainId": 1,
        "data": data,
    }
    signed = web3.eth.account.sign_transaction(transaction, key)
    tx_hash = web3.eth.sendRawTransaction(signed.rawTransaction)
    print(tx_hash)
    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)


def get_account():
    with open("badger_deployer_keystore.json") as keyfile:
        encrypted_key = keyfile.read()
        private_key = web3.eth.account.decrypt(encrypted_key, "-")
        return private_key


def deploy_contract(deployer, abi, bytecode):
    key = get_account()
    # web3.eth.defaultAccount = web3.eth.accounts[0]

    Contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = web3.eth.getTransactionCount("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b")

    # tx_hash = ProxyAdmin.constructor().transact()
    # tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)

    deploy_txn = Contract.constructor().buildTransaction(
        {"chainId": 1, "gas": 3000000, "gasPrice": gas_price, "nonce": nonce,}
    )

    signed_txn = web3.eth.account.sign_transaction(deploy_txn, private_key=key)
    tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
    print("deploy", tx_hash)
    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)

    return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)


def deploy_proxy_admin():
    abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["ProxyAdmin"]["bytecode"]

    key = get_account()

    proxyAdmin = deploy_contract(key, abi, bytecode)

    return Contract.from_abi(
        "ProxyAdmin", web3.toChecksumAddress(proxyAdmin.address), abi,
    )


def deploy_from_bytecode(contractName, abi, bytecode, deployer):
    # print(str(acct.address))
    # web3.eth.defaultAccount = str(accounts[0])

    # ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)

    # tx_hash = ProxyAdmin.constructor(
    #     logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    # ).transact()

    # tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    # transaction = web3.eth.getTransaction(tx_hash)

    # contract = web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

    # return Contract.from_abi(contractName, contract.address, logicAbi)
    return False


def deploy_proxy(contractName, logicAbi, logic, proxyAdmin, initializer, deployer):
    abi = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["bytecode"]
    key = get_account()

    # print(str(acct.address))
    # web3.eth.defaultAccount = str(accounts[0])

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = web3.eth.getTransactionCount("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b")
    # tx_hash = ProxyAdmin.constructor(
    #     logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    # ).transact()

    deploy_txn = ProxyAdmin.constructor(
        logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    ).buildTransaction(
        {"chainId": 1, "gas": 6000000, "gasPrice": gas_price, "nonce": nonce,}
    )

    signed_txn = web3.eth.account.sign_transaction(deploy_txn, private_key=key)
    tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
    print("tx_hash", tx_hash)
    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash, timeout=300)
    contract = web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

    print("deployed", contract.address)
    return Contract.from_abi(contractName, contract.address, logicAbi)


# def deploy_proxy_address(logicAddress, proxyAdmin, encoded_initializer):
#     abi = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["abi"]
#     bytecode = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["bytecode"]

#     # print(str(acct.address))
#     web3.eth.defaultAccount = str(accounts[0])
#     print(accounts[0])

#     ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)
#     print(logicAddress, proxyAdmin, web3.toBytes(hexstr=encoded_initializer))

#     tx_hash = ProxyAdmin.constructor(
#         logicAddress, proxyAdmin, web3.toBytes(hexstr=encoded_initializer)
#     ).transact()

#     tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
#     transaction = web3.eth.getTransaction(tx_hash)

#     contract = web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

#     return contract.address
