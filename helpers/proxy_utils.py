from brownie import *
from brownie.utils import color
from enum import Enum
from helpers.registry import registry
from eth_account import Account


def deploy_contract(deployer, abi, bytecode):
    web3.eth.defaultAccount = web3.eth.accounts[0]

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = ProxyAdmin.constructor().transact()
    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)

    return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)


def deploy_proxy_admin():
    abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["ProxyAdmin"]["bytecode"]

    proxyAdmin = deploy_contract(web3.eth.accounts[0], abi, bytecode)

    return Contract.from_abi(
        "ProxyAdmin", web3.toChecksumAddress(proxyAdmin.address), abi,
    )


def deploy_proxy(contractName, logicAbi, logic, proxyAdmin, initializer, deployer):
    abi = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["bytecode"]

    # print(str(acct.address))
    web3.eth.defaultAccount = str(accounts[0])
    print(accounts[0])

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)

    tx_hash = ProxyAdmin.constructor(
        logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    ).transact()

    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    transaction = web3.eth.getTransaction(tx_hash)

    contract = web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

    return Contract.from_abi(contractName, contract.address, logicAbi)


def deploy_proxy_address(logicAddress, proxyAdmin, encoded_initializer):
    abi = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["bytecode"]

    # print(str(acct.address))
    web3.eth.defaultAccount = str(accounts[0])
    print(accounts[0])

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)
    print(logicAddress, proxyAdmin, web3.toBytes(hexstr=encoded_initializer))

    tx_hash = ProxyAdmin.constructor(
        logicAddress, proxyAdmin, web3.toBytes(hexstr=encoded_initializer)
    ).transact()

    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    transaction = web3.eth.getTransaction(tx_hash)

    contract = web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

    return contract.address
