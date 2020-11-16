import json
from helpers.time_utils import daysToSeconds
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from brownie import *
from helpers.constants import AddressZero, EmptyBytes32
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, sett_config
from scripts.systems.sett_system import deploy_sett_system


def deploy_geyser(badger, stakingToken):
    pool_input = DotMap(
        stakingToken=stakingToken.address,
        initialDistributionToken=badger.token.address,
        initialSharesPerToken=badger_config.geyserParams.initialSharesPerToken,
        founderRewardAddress=badger.devMultisig.address,
        founderRewardPercentage=badger_config.geyserParams.founderRewardPercentage,
    )

    return deploy_proxy(
        "BadgerGeyser",
        BadgerGeyser.abi,
        badger.logic.BadgerGeyser.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerGeyser.initialize.encode_input(
            pool_input["stakingToken"],
            pool_input["initialDistributionToken"],
            pool_input["initialSharesPerToken"],
            badger_config.geyserParams.badgerDistributionStart,
            pool_input["founderRewardAddress"],
            pool_input["founderRewardPercentage"],
        ),
        badger.deployer,
    )


def print_to_file(badger, path):
    system = {
        "deployer": badger.deployer.address,
        "devProxyAdmin": badger.devProxyAdmin.address,
        "daoProxyAdmin": badger.daoProxyAdmin.address,
        "devMultisig": badger.devMultisig.address,
        "token": badger.token.address,
        "dao": {},
        "pools": {},
        "sett": {},
        "daoBadgerTimelock": badger.daoBadgerTimelock.address,
        "teamVesting": badger.teamVesting.address,
        "badgerHunt": badger.badgerHunt.address,
        "badgerTree": badger.badgerTree.address,
    }

    print(badger.dao)

    # DAO
    for key, value in badger.dao.items():
        system["dao"][key] = value.address

    # Pools
    system["pools"]["sett"] = {}
    system["pools"]["sett"]["native"] = {}
    system["pools"]["sett"]["pickle"] = {}
    system["pools"]["sett"]["harvest"] = {}

    for key, value in badger.pools.sett.native.items():
        system["pools"]["sett"]["native"][key] = value.address

    for key, value in badger.pools.sett.pickle.items():
        system["pools"]["sett"]["pickle"][key] = value.address

    for key, value in badger.pools.sett.harvest.items():
        system["pools"]["sett"]["harvest"][key] = value.address

    # Sett
    system["sett"]["logic"] = {}
    system["sett"]["native"] = {}
    system["sett"]["pickle"] = {}
    system["sett"]["harvest"] = {}
    system["sett"]["rewards"] = {}

    for key, value in badger.sett.logic.items():
        system["sett"]["logic"][key] = value.address

    for key, value in badger.sett.native.items():
        if key is not "strategies":
            system["sett"]["native"][key] = value.address

    for key, value in badger.sett.pickle.items():
        if key is not "strategies":
            system["sett"]["pickle"][key] = value.address

    for key, value in badger.sett.harvest.items():
        if key is not "strategies":
            system["sett"]["harvest"][key] = value.address

    for key, value in badger.sett.rewards.items():
        system["sett"]["harvest"][key] = value.address

    system["sett"]["native"]["strategies"] = {}
    system["sett"]["pickle"]["strategies"] = {}
    system["sett"]["harvest"]["strategies"] = {}

    for key, value in badger.sett.native.strategies.items():
        system["sett"]["native"]["strategies"][key] = value.address

    for key, value in badger.sett.pickle.strategies.items():
        system["sett"]["pickle"]["strategies"][key] = value.address

    for key, value in badger.sett.harvest.strategies.items():
        system["sett"]["harvest"]["strategies"][key] = value.address

    with open(path, "w") as outfile:
        json.dump(system, outfile)


def deploy_badger(systems, deployer):
    """
    Deploy fresh badger system
    """
    badger = BadgerSystem(badger_config, systems)
    badger.deployer = deployer
    badger.devProxyAdmin = deploy_proxy_admin()
    badger.daoProxyAdmin = deploy_proxy_admin()
    badger.proxyAdmin = badger.devProxyAdmin

    # Deploy Dev Multisig (Later Connect)
    multisigParams = badger_config["devMultisigParams"]
    multisigParams.owners = [deployer.address]

    badger.devMultisig = systems.gnosis_safe.deployGnosisSafe(multisigParams, deployer)

    # Deploy DAO
    daoParams = badger_config["daoParams"]
    daoParams.holders = [deployer.address]
    daoParams.stakes = [daoParams.initialSupply]

    badger.dao = systems.aragon.deployCompanyDao(daoParams, deployer)

    # Alias for badger token
    badger.token = badger.dao.token

    # Deploy necessary logic contracts
    badger.logic = DotMap(
        SmartVesting=SmartVesting.deploy({"from": deployer}),
        SmartTimelock=SmartTimelock.deploy({"from": deployer}),
        BadgerGeyserEscrow=BadgerGeyserEscrow.deploy({"from": deployer}),
        BadgerGeyser=BadgerGeyser.deploy({"from": deployer}),
        BadgerTree=BadgerTree.deploy({"from": deployer}),
        BadgerHunt=BadgerHunt.deploy({"from": deployer}),
        SimpleTimelock=SimpleTimelock.deploy({"from": deployer}),
    )

    # Deploy Rewards
    guardian = deployer
    updater = deployer

    badger.badgerTree = deploy_proxy(
        "BadgerTree",
        BadgerTree.abi,
        badger.logic.BadgerTree.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerTree.initialize.encode_input(
            badger.devMultisig, updater, guardian
        ),
        deployer,
    )

    # Deploy Sett Subsystem
    badger.sett = deploy_sett_system(badger, deployer)

    # Deploy timelocks & vesting
    # DAO Badger Vesting
    badger.daoBadgerTimelock = deploy_proxy(
        "SimpleTimelock",
        SimpleTimelock.abi,
        badger.logic.SimpleTimelock.address,
        AddressZero,
        badger.logic.SimpleTimelock.initialize.encode_input(
            badger.token, badger.dao.agent, badger_config.tokenLockParams.releaseTime
        ),
        badger.deployer,
    )

    # Team Badger Vesting
    badger.teamVesting = deploy_proxy(
        "SmartVesting",
        SmartVesting.abi,
        badger.logic.SmartVesting.address,
        AddressZero,
        badger.logic.SmartVesting.initialize.encode_input(
            badger.token,
            badger.devMultisig,
            badger.dao.agent,
            badger_config.teamVestingParams.startTime,
            badger_config.teamVestingParams.cliffDuration,
            badger_config.teamVestingParams.totalDuration,
        ),
        badger.deployer,
    )

    badger.pools = DotMap(
        sett=DotMap(native=DotMap(), pickle=DotMap(), harvest=DotMap())
    )

    # Deploy staking pools
    badger.pools.sett.native.renCrv = deploy_geyser(badger, badger.sett.native.renCrv)
    badger.pools.sett.native.sbtcCrv = deploy_geyser(badger, badger.sett.native.sbtcCrv)
    badger.pools.sett.native.tbtcCrv = deploy_geyser(badger, badger.sett.native.tbtcCrv)
    badger.pools.sett.native.badger = deploy_geyser(badger, badger.sett.native.badger)

    badger.pools.sett.pickle.renCrv = deploy_geyser(badger, badger.sett.pickle.renCrv)
    badger.pools.sett.harvest.renCrv = deploy_geyser(badger, badger.sett.harvest.renCrv)

    # Deploy Hunt
    badger.badgerHunt = deploy_proxy(
        "BadgerHunt",
        BadgerHunt.abi,
        badger.logic.BadgerHunt.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerHunt.initialize.encode_input(
            badger.token,
            EmptyBytes32,
            daysToSeconds(1),
            2000,
            badger_config.huntParams.startTime,
        ),
        badger.deployer,
    )

    print_to_file(badger, "local.json")

    # print("Transfer Token")
    # Distribute initial Badger supply
    # badger.token.transfer(
    #     badger.daoBadgerTimelock,
    #     badger_config.tokenLockParams.badgerLockAmount,
    #     {"from": deployer},
    # )


def connect_badger(registry):
    """
    Connect to existing badger deployment
    """
    assert False


class BadgerSystem:
    def __init__(self, config, systems):
        self.config = config
        self.systems = systems

