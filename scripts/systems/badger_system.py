import json
from scripts.systems.uniswap_system import UniswapSystem, connect_uniswap
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.time_utils import daysToSeconds
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from brownie import *
from helpers.constants import AddressZero, EmptyBytes32
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, sett_config, badger_total_supply
from scripts.systems.sett_system import (
    deploy_controller,
    deploy_sett,
    deploy_sett_system,
    deploy_strategy,
)


def deploy_geyser(badger, stakingToken):
    pool_input = DotMap(
        stakingToken=stakingToken.address,
        initialDistributionToken=badger.token.address,
    )

    return deploy_proxy(
        "BadgerGeyser",
        BadgerGeyser.abi,
        badger.logic.BadgerGeyser.address,
        badger.devProxyAdmin.address,
        badger.logic.BadgerGeyser.initialize.encode_input(
            pool_input["stakingToken"],
            pool_input["initialDistributionToken"],
            badger_config.geyserParams.badgerDistributionStart,
            badger.devMultisig.address,
            badger.rewardsEscrow.address,
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

    # TODO: Replace with prod values
    badger.deployer = deployer
    badger.keeper = deployer
    badger.guardian = deployer

    badger.devProxyAdmin = deploy_proxy_admin()
    badger.daoProxyAdmin = deploy_proxy_admin()
    badger.proxyAdmin = badger.devProxyAdmin

    # Deploy Dev Multisig (Later Connect)
    multisigParams = badger_config["devMultisigParams"]
    multisigParams.owners = [deployer.address]

    print("Deploy Dev Multisig")
    badger.devMultisig = systems.gnosis_safe.deployGnosisSafe(multisigParams, deployer)

    print("Connect to DAO")
    badger.dao = DotMap(
        token=Contract.from_abi(
            "MiniMeToken",
            dao_config.token,
            registry.aragon.artifacts.MiniMeToken["abi"],
            deployer,
        ),
        kernel=Contract.from_abi(
            "Agent", dao_config.kernel, registry.aragon.artifacts.Agent["abi"], deployer
        ),
        agent=Contract.from_abi(
            "Agent", dao_config.agent, registry.aragon.artifacts.Agent["abi"], deployer
        ),
    )

    # badger.dao = systems.aragon.deployCompanyDao(daoParams, deployer)

    # Alias for badger token
    badger.token = badger.dao.token

    # Requires ganache --unlock for initial owner
    badger.token.transfer(
        deployer, badger_total_supply, {"from": dao_config.initialOwner}
    )

    # Deploy necessary logic contracts
    print("Deploy Logic Contracts")
    badger.logic = DotMap(
        SmartVesting=SmartVesting.deploy({"from": deployer}),
        SmartTimelock=SmartTimelock.deploy({"from": deployer}),
        RewardsEscrow=RewardsEscrow.deploy({"from": deployer}),
        BadgerGeyser=BadgerGeyser.deploy({"from": deployer}),
        BadgerTree=BadgerTree.deploy({"from": deployer}),
        BadgerHunt=BadgerHunt.deploy({"from": deployer}),
        SimpleTimelock=SimpleTimelock.deploy({"from": deployer}),
    )

    # Deploy Rewards
    guardian = deployer
    updater = deployer

    print("Deploy Rewards Infrastructure")
    # TODO: Should be owned by devMultisig
    badger.rewardsEscrow = deploy_proxy(
        "RewardsEscrow",
        RewardsEscrow.abi,
        badger.logic.RewardsEscrow.address,
        badger.devProxyAdmin.address,
        badger.logic.RewardsEscrow.initialize.encode_input(deployer),
        deployer,
    )

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
    print("Deploy Sett")
    badger.sett = deploy_sett_system(badger, deployer)

    # Deploy timelocks & vesting
    # DAO Badger Vesting
    print("Deploy Locks & Vesting")
    badger.daoBadgerTimelock = deploy_proxy(
        "SimpleTimelock",
        SimpleTimelock.abi,
        badger.logic.SimpleTimelock.address,
        AddressZero,
        badger.logic.SimpleTimelock.initialize.encode_input(
            badger.token, badger.dao.agent, badger_config.tokenLockParams.lockDuration
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

    print("Deploy Rewards Pools")
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

    print("Deploy Airdrop")
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
            daysToSeconds(1),
            badger.rewardsEscrow,
        ),
        badger.deployer,
    )

    print("Printing contract addresses to local.json")
    print_to_file(badger, "local.json")

    # Upgradeable Contracts
    badger.contracts = [
        badger.badgerTree,
        badger.badgerHunt,
        badger.rewardsEscrow,
        badger.sett.native.controller,
        badger.sett.harvest.controller,
        badger.sett.pickle.controller,
        badger.sett.native.badger,
        badger.sett.native.renCrv,
        badger.sett.native.sBtcCrv,
        badger.sett.native.tBtcCrv,
        badger.sett.harvest.renCrv,
        badger.sett.pickle.renCrv,
        badger.sett.native.strategies.badger,
        badger.sett.native.strategies.renCrv,
        badger.sett.native.strategies.sBtcCrv,
        badger.sett.native.strategies.tBtcCrv,
        badger.sett.harvest.strategies.renCrv,
        badger.sett.pickle.strategies.renCrv,
        badger.sett.rewards.badger,
        badger.teamVesting,
        badger.daoBadgerTimelock,
        badger.pools.sett.native.renCrv,
        badger.pools.sett.native.sBtcCrv,
        badger.pools.sett.native.tBtcCrv,
        badger.pools.sett.harvest.renCrv,
        badger.pools.sett.pickle.renCrv,
    ]

    return badger


def config_badger(badger):
    """
    Set initial conditions on immediate post-deploy Badger

    Transfer tokens to thier initial locations
        - Rewards Escrow (50%, minus tokens initially distributed via Sett Special StakingRewards)
        - Badger Hurt (15%)
        - DAO Timelock (35%)
    """
    deployer = badger.deployer

    # Distribute initial Badger supply

    # DAO Timelock
    badger.token.transfer(
        badger.daoBadgerTimelock,
        badger_config.tokenLockParams.badgerLockAmount,
        {"from": deployer},
    )

    # Geyser Signals
    """
        These signals are used to calculate the rewards distributions distributed via BadgerTree. The tokens are actually held in the RewardsEscrow and sent to the BadgerTree as needed.

        The escrow will only send 1-2 days worth of rewards at a time to the RewardsTree as another failsafe mechanism.

        renbtcCRV — 76750 $BADGER
        sbtcCRV — 76,750 $BADGER
        tbtcCRV — 76,750 $BADGER
        Badger — 90,000 $BADGER
        Badger <>wBTC Uniswap LP — 130,000 $BADGER
        Super Sett
        Pickle renbtcCRV — 76,750 $BADGER
        Harvest renbtc CRV — 76,750 $BADGER
    """
    startTime = badger_config.geyserParams.badgerDistributionStart

    # params = badger_config.geyserParams.unlockSchedules.badger[0]
    # badger.pools.sett.native.badger.signalTokenLock(badger.token, params.amount, params.duration, startTime)

    # Approve Recipients on RewardsEscrow
    badger.rewardsEscrow.approveRecipient(
        badger.pools.sett.native.sbtcCrv, {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.pools.sett.native.renCrv, {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.pools.sett.native.tbtcCrv, {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.pools.sett.pickle.renCrv, {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.pools.sett.harvest.renCrv, {"from": deployer}
    )

    # Signal Locks
    params = badger_config.geyserParams.unlockSchedules.bSbtcCrv[0]

    badger.rewardsEscrow.signalTokenLock(
        badger.pools.sett.native.sbtcCrv,
        badger.token,
        params.amount,
        params.duration,
        startTime,
        {"from": deployer},
    )

    params = badger_config.geyserParams.unlockSchedules.bRenCrv[0]
    badger.rewardsEscrow.signalTokenLock(
        badger.pools.sett.native.renCrv,
        badger.token,
        params.amount,
        params.duration,
        startTime,
        {"from": deployer},
    )

    params = badger_config.geyserParams.unlockSchedules.bTbtcCrv[0]
    badger.rewardsEscrow.signalTokenLock(
        badger.pools.sett.native.tbtcCrv,
        badger.token,
        params.amount,
        params.duration,
        startTime,
        {"from": deployer},
    )

    params = badger_config.geyserParams.unlockSchedules.bSuperRenCrvPickle[0]
    badger.rewardsEscrow.signalTokenLock(
        badger.pools.sett.pickle.renCrv,
        badger.token,
        params.amount,
        params.duration,
        startTime,
        {"from": deployer},
    )

    params = badger_config.geyserParams.unlockSchedules.bSuperRenCrvHarvest[0]
    badger.rewardsEscrow.signalTokenLock(
        badger.pools.sett.harvest.renCrv,
        badger.token,
        params.amount,
        params.duration,
        startTime,
        {"from": deployer},
    )

    # Staking Rewards Pools

    params = badger_config.geyserParams.unlockSchedules.badger[0]
    toEscrow = badger_config.rewardsEscrowBadgerAmount

    badger.token.transfer(
        badger.sett.rewards.badger, params.amount, {"from": deployer},
    )

    badger.sett.rewards.badger.notifyRewardAmount(params.amount, {"from": deployer})

    toEscrow = toEscrow - params.amount

    # Rewards Escrow
    badger.token.transfer(
        badger.rewardsEscrow, toEscrow, {"from": deployer},
    )

    # Badger Hunt
    badger.token.transfer(
        badger.badgerHunt, badger_config.huntParams.badgerAmount, {"from": deployer},
    )


def start_rewards(badger):
    deployer = badger.deployer

    # Start Rewards on StakingEscrow contracts
    params = badger_config.geyserParams.unlockSchedules.badger[0]

    badger.token.transfer(
        badger.sett.rewards.badger, params.amount, {"from": deployer},
    )

    assert badger.token.balanceOf(badger.sett.rewards.badger) >= params.amount
    assert badger.sett.rewards.badger.rewardsToken() == badger.token

    badger.sett.rewards.badger.notifyRewardAmount(params.amount, {"from": deployer})


def connect_badger(registry):
    """
    Connect to existing badger deployment
    """
    assert False


class BadgerSystem:
    def __init__(self, config, systems, deployer):
        self.config = config
        self.systems = systems
        self.contracts_static = []
        self.contracts_upgradeable = []

        # TODO: Replace with prod values
        self.deployer = deployer
        self.keeper = deployer
        self.guardian = deployer

        self.devProxyAdmin = deploy_proxy_admin()
        self.daoProxyAdmin = deploy_proxy_admin()
        self.proxyAdmin = self.devProxyAdmin
        self.logic = DotMap()
        self.sett_system = DotMap(
            controllers=DotMap(), vaults=DotMap(), strategies=DotMap(), rewards=DotMap()
        )
        self.geysers = DotMap()

        self.connect_dao()
        self.connect_multisig()
        self.connect_uniswap()

    def track_contract_static(self, contract):
        self.contracts_static.append(contract)

    def track_contract_upgradeable(self, contract):
        self.contracts_upgradeable.append(contract)

    # ===== Contract Connectors =====
    def connect_dao(self):
        deployer = self.deployer
        self.dao = DotMap(
            token=Contract.from_abi(
                "MiniMeToken",
                badger_config.dao.token,
                registry.aragon.artifacts.MiniMeToken["abi"],
                deployer,
            ),
            kernel=Contract.from_abi(
                "Agent",
                badger_config.dao.kernel,
                registry.aragon.artifacts.Agent["abi"],
                deployer,
            ),
            agent=Contract.from_abi(
                "Agent",
                badger_config.dao.agent,
                registry.aragon.artifacts.Agent["abi"],
                deployer,
            ),
        )

        self.token = self.dao.token

    def connect_multisig(self):
        deployer = self.deployer

        multisigParams = badger_config["devMultisigParams"]
        multisigParams.owners = [deployer.address]

        print("Deploy Dev Multisig")
        self.devMultisig = connect_gnosis_safe(badger_config.multisig.address)
        self.updater = deployer
        self.guardian = deployer

    def connect_uniswap(self):
        self.uniswap = UniswapSystem()

    # ===== Deployers =====

    def add_controller(self, id):
        deployer = self.deployer
        controller = deploy_controller(self, deployer)
        self.sett_system.controllers[id] = controller
        self.track_contract_upgradeable(controller)
        return controller

    def deploy_core_logic(self):
        deployer = self.deployer
        self.logic = DotMap(
            SmartVesting=SmartVesting.deploy({"from": deployer}),
            SmartTimelock=SmartTimelock.deploy({"from": deployer}),
            RewardsEscrow=RewardsEscrow.deploy({"from": deployer}),
            BadgerGeyser=BadgerGeyser.deploy({"from": deployer}),
            BadgerTree=BadgerTree.deploy({"from": deployer}),
            BadgerHunt=BadgerHunt.deploy({"from": deployer}),
            SimpleTimelock=SimpleTimelock.deploy({"from": deployer}),
        )

    def deploy_sett_core_logic(self):
        deployer = self.deployer
        self.logic.Controller = Controller.deploy({"from": deployer})
        self.logic.Sett = Sett.deploy({"from": deployer})
        self.logic.StakingRewards = StakingRewards.deploy({"from": deployer})

    def deploy_rewards_escrow(self):
        deployer = self.deployer
        self.rewardsEscrow = deploy_proxy(
            "RewardsEscrow",
            RewardsEscrow.abi,
            self.logic.RewardsEscrow.address,
            self.devProxyAdmin.address,
            self.logic.RewardsEscrow.initialize.encode_input(deployer),
            deployer,
        )
        self.track_contract_upgradeable(self.rewardsEscrow)

    def deploy_badger_tree(self):
        deployer = self.deployer
        self.badgerTree = deploy_proxy(
            "BadgerTree",
            BadgerTree.abi,
            self.logic.BadgerTree.address,
            self.devProxyAdmin.address,
            self.logic.BadgerTree.initialize.encode_input(
                self.devMultisig, self.updater, self.guardian
            ),
            deployer,
        )
        self.track_contract_upgradeable(self.badgerTree)

    def deploy_badger_hunt(self):
        deployer = self.deployer
        self.badgerHunt = deploy_proxy(
            "BadgerHunt",
            BadgerHunt.abi,
            self.logic.BadgerHunt.address,
            self.devProxyAdmin.address,
            self.logic.BadgerHunt.initialize.encode_input(
                self.token,
                EmptyBytes32,
                daysToSeconds(1),
                2000,
                badger_config.huntParams.startTime,
                daysToSeconds(1),
                self.rewardsEscrow,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.badgerHunt)

    def deploy_dao_badger_timelock(self):
        deployer = self.deployer
        self.daoBadgerTimelock = deploy_proxy(
            "SimpleTimelock",
            SimpleTimelock.abi,
            self.logic.SimpleTimelock.address,
            AddressZero,
            self.logic.SimpleTimelock.initialize.encode_input(
                self.token, self.dao.agent, badger_config.tokenLockParams.lockDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.daoBadgerTimelock)

    def deploy_dao_digg_timelock(self):
        deployer = self.deployer

    def deploy_team_vesting(self):
        deployer = self.deployer

        self.teamVesting = deploy_proxy(
            "SmartVesting",
            SmartVesting.abi,
            self.logic.SmartVesting.address,
            AddressZero,
            self.logic.SmartVesting.initialize.encode_input(
                self.token,
                self.devMultisig,
                self.dao.agent,
                badger_config.teamVestingParams.startTime,
                badger_config.teamVestingParams.cliffDuration,
                badger_config.teamVestingParams.totalDuration,
            ),
            self.deployer,
        )
        self.track_contract_upgradeable(self.teamVesting)

    def add_logic(self, name, BrownieArtifact):
        deployer = self.deployer
        self.logic[name] = BrownieArtifact.deploy({"from": deployer})

    def add_sett(self, id, token, controller, name, symbol):
        deployer = self.deployer
        proxyAdmin = self.devProxyAdmin
        governance = deployer
        keeper = deployer

        print(token, controller, governance, keeper, name, symbol)

        sett = deploy_proxy(
            "Sett",
            Sett.abi,
            self.logic.Sett.address,
            proxyAdmin.address,
            self.logic.Sett.initialize.encode_input(
                token, controller, governance, keeper, name, symbol
            ),
            deployer,
        )
        self.sett_system.vaults[id] = sett
        self.track_contract_upgradeable(sett)
        return sett

    def add_strategy(self, id, strategyName, controller, params):
        # TODO: Replace with prod permissions config
        deployer = self.deployer

        strategy = deploy_strategy(self, strategyName, controller, params, deployer,)

        self.sett_system.strategies[id] = strategy
        self.track_contract_upgradeable(strategy)
        return strategy

    def add_geyser(self, distToken, id):
        deployer = self.deployer
        geyser = deploy_geyser(self, distToken)
        self.geysers[id] = geyser
        self.track_contract_upgradeable(geyser)
        return geyser

    def deploy_sett_staking_rewards(self, id, stakingToken, distToken):
        deployer = self.deployer

        print(deployer, distToken, stakingToken)

        rewards = deploy_proxy(
            "StakingRewards",
            StakingRewards.abi,
            self.logic.StakingRewards.address,
            self.devProxyAdmin.address,
            self.logic.StakingRewards.initialize.encode_input(
                deployer, distToken, stakingToken
            ),
            deployer,
        )

        self.sett_system.rewards[id] = rewards
        self.track_contract_upgradeable(rewards)
        return rewards

    # ===== Function Call Macros =====

    def wire_up_sett(self, vault, strategy, controller):
        deployer = self.deployer

        want = strategy.want()
        vault_want = vault.token()

        assert vault_want == want

        controller.setVault(want, vault, {"from": deployer})

        controller.approveStrategy(
            want, strategy, {"from": deployer},
        )

        controller.setStrategy(
            want, strategy, {"from": deployer},
        )

    def distribute_staking_rewards(self, rewards, amount):
        deployer = self.deployer

        self.token.transfer(
            rewards, amount, {"from": deployer},
        )

        assert self.token.balanceOf(rewards) >= amount
        assert rewards.rewardsToken() == self.token
        rewards.notifyRewardAmount(amount, {"from": deployer})

    def signal_initial_geyser_rewards(self, id, params):
        deployer = self.deployer
        startTime = badger_config.geyserParams.badgerDistributionStart
        geyser = self.getGeyser(id)

        self.rewardsEscrow.approveRecipient(geyser, {"from": deployer})

        self.rewardsEscrow.signalTokenLock(
            self.token, params.amount, params.duration, startTime, {"from": deployer},
        )

    # ===== Getters =====

    def getGeyser(self, id):
        return self.geysers[id]

    def getController(self, id):
        return self.sett_system.controllers[id]

    def getSett(self, id):
        return self.sett_system.vaults[id]

    def getSettRewards(self, id):
        return self.sett_system.rewards[id]

    def getStrategy(self, id):
        return self.sett_system.strategies[id]

    def getStrategyWant(self, id):
        return interface.IERC20(self.sett_system.strategies[id].want())
