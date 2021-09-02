from dotmap import DotMap
import os
import json
import time
from brownie import (
    accounts,
    network,
    SettV3,
    AdminUpgradeabilityProxy,
    Controller,
    BadgerRegistry,
    BadgerTreeV2,
    KeeperAccessControl,
    RewardsLogger,
    ProxyAdmin,
    VipCappedGuestListBbtcUpgradeable,
    WarRoomGatedProxy
)
from scripts.connect_account import connect_account
from helpers.sett.strategy_registry import contract_name_to_artifact
from helpers.constants import AddressZero

from rich.console import Console

console = Console()

sleep_between_tx = 1

# Name of contracts to deploy
contractNames = [
    "BadgerRegistry",
    "KeeperAccessControl",
    "Controller",
    "RewardsLogger",
    "BadgerTreeV2",
    "WarRoomGatedProxy",
    "VipCappedGuestListBbtcUpgradeable",
    "SettV3",
]

def main():
    path = os.getcwd() + "/arbirtum_logic.json"
    with open(path) as f:
        data = json.load(f)

    proxyAdminDev = data["proxyAdminDev"]

    # Connect to deployer account from local Keystore
    dev = connect_account()

    console.print("[blue]Fetching or deploying logic...[/blue]")
    logic = deploy_logic(dev, data, contractNames)

    console.print("[blue]Deploying proxies...[/blue]")

    # == Deploy BadgerRegistry == #
    args = [dev.address] # Governance
    registry = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[0]],
        contractNames[0],
        args
    )
    # == Deploy KeeperAccessControl == #
    args = [dev.address] # initialAdmin_
    keeper = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[1]],
        contractNames[1],
        args
    )
    # == Deploy Controller == #
    args = [
        dev.address, # Governance
        dev.address, #Strategist
        keeper.address, # Keeper
        dev.address # Rewards
    ]
    controller = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[2]],
        contractNames[2],
        args
    )
    # == Deploy RewardsLogger == #
    args = [
        dev.address, # initialAdmin_
        dev.address # initialManager_
    ] 
    logger = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[3]],
        contractNames[3],
        args
    )
    # == Deploy BadgerTreeV2 == #
    args = [
        dev.address, # admin
        dev.address, # initialProposer
        dev.address # initialValidator
    ] 
    tree = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[4]],
        contractNames[4],
        args
    )
    # == Deploy WarRoomGatedProxy == #
    args = [
        dev.address, # initialAdmin_
        [] # initialAccounts_
    ] 
    guardian = deploy_proxyContract(
        dev, 
        proxyAdminDev,
        logic[contractNames[5]],
        contractNames[5],
        args
    )

def deploy_logic(dev, data, contractNames):
    logic = DotMap()

    for name in contractNames:
        if name not in data:
            artifact = contract_name_to_artifact(name)
            contractLogic = artifact.deploy({"from": dev})
            data.append({name: contractLogic.address})
            logic[name] = contractLogic
            console.print(name, "[green]logic deployed![/green]")
        else:
            artifact = contract_name_to_artifact(name)
            logic[name] = artifact.at(data[name])
            console.print(name, "[green]logic fetched![/green]")

    return logic

def deploy_proxyContract(dev, proxyAdmin, logic, name, args):
    console.print(name, "arguments: ", args)

    proxy = AdminUpgradeabilityProxy.deploy(
        logic,
        proxyAdmin,
        logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    console.print(name, "[green]proxy deployed![/green]")

    ## We delete from deploy and then fetch again so we can interact
    artifact = contract_name_to_artifact(name)
    AdminUpgradeabilityProxy.remove(proxy)
    return artifact.at(proxy.address)

