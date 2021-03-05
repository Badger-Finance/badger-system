from brownie import *
from brownie.network.gas.strategies import GasNowStrategy

from helpers.registry.artifacts import artifacts

gas_strategy = GasNowStrategy("rapid")


def deploy_proxy_admin(deployer):
    abi = artifacts.open_zeppelin["ProxyAdmin"]["abi"]
    bytecode = artifacts.open_zeppelin["ProxyAdmin"]["bytecode"]

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)

    deploy_txn = ProxyAdmin.constructor().buildTransaction()
    tx = deployer.transfer(data=deploy_txn["data"])

    return Contract.from_abi(
        "ProxyAdmin", web3.toChecksumAddress(tx.contract_address), abi,
    )


def deploy_proxy_uninitialized(contractName, logicAbi, logic, proxyAdmin, deployer):
    abi = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["abi"]
    bytecode = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["bytecode"]

    AdminUpgradeabilityProxy = web3.eth.contract(abi=abi, bytecode=bytecode)

    deploy_txn = AdminUpgradeabilityProxy.constructor(
        logic, proxyAdmin, web3.toBytes(hexstr="0x")
    ).buildTransaction()

    tx = deployer.transfer(data=deploy_txn["data"], gas_price=40000000000)

    return Contract.from_abi(contractName, tx.contract_address, logicAbi)


def deploy_proxy(contractName, logicAbi, logic, proxyAdmin, initializer, deployer):
    abi = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["abi"]
    bytecode = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["bytecode"]

    AdminUpgradeabilityProxy = web3.eth.contract(abi=abi, bytecode=bytecode)

    deploy_txn = AdminUpgradeabilityProxy.constructor(
        logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    ).buildTransaction()

    tx = deployer.transfer(data=deploy_txn["data"])

    print("Deployng contract:", contractName, "address:", tx.contract_address)
    return Contract.from_abi(contractName, tx.contract_address, logicAbi)

