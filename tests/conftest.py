import pytest
import json
from brownie import (
    Wei,
    BadgerHunt,
    accounts,
)

from config.badger_config import badger_config, digg_config, sett_config
from scripts.deploy.deploy_badger import deploy_flow
from scripts.systems.badger_system import connect_badger
from scripts.systems.badger_minimal import deploy_badger_minimal
from scripts.systems.digg_minimal import deploy_digg_minimal
from scripts.systems.constants import SettType
from helpers.token_utils import distribute_test_ether
from helpers.registry import registry
from helpers.network import network_manager
from tests.helpers import distribute_from_whales
from tests.sett.fixtures import (
    SushiBadgerLpOptimizerMiniDeploy,
    DiggRewardsMiniDeploy,
    BadgerLpMetaFarmMiniDeploy,
    BadgerRewardsMiniDeploy,
    CurveGaugeRenBtcMiniDeploy,
    CurveGaugeSBtcMiniDeploy,
    CurveGaugeTBtcMiniDeploy,
    HarvestMetaFarmMiniDeploy,
    SushiBadgerWBtcMiniDeploy,
    SushiDiggWbtcLpOptimizerMiniDeploy,
    UniDiggWbtcLpMiniDeploy,
    SushiClawUSDCMiniDeploy,
    PancakeMiniDeploy,
    SushiWbtcIbBtcLpOptimizerMiniDeploy,
    UnitProtocolRenBtcMiniDeploy,
    UniGenericLpMiniDeploy,
    DiggStabilizeMiniDeploy
)


def generate_sett_test_config(settsToRun, runTestSetts, runProdSetts=False):
    setts = []
    for settId in settsToRun:
        if runTestSetts:
            setts.append({"id": settId, "mode": "test"})
        if runProdSetts:
            setts.append({"id": settId, "mode": "prod"})
    return setts


# ===== Sett + Strategy Test Configuration =====

settsToRun = [
    "native.unitRenBtc",
    # "native.badger",
    # "native.renCrv",
    # "native.sbtcCrv",
    # "native.tbtcCrv",
    # "harvest.renCrv",
    # "native.uniBadgerWbtc",
    # "native.sushiBadgerWbtc",
    # "native.sushiWbtcEth",
    # "native.sushiWbtcIbBtc",
    # "native.sushiWbtcIbBtc",
    # "native.uniWbtcIbBtc",
]

yearnSettsToRun = [
    "yearn.bvyWBTC",
]

diggSettsToRun = [
    "native.digg",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
]

clawSettsToRun = [
    "native.sushiSClawUSDC",
    "native.sushiBClawUSDC",
]

# Setts w/ backing collateral for testing the CLAW emp contract.
clawSettsSytheticTestsToRun = [
    "native.badger",
    "native.sushiWbtcEth",
]

bscSettsToRun = [
    "native.pancakeBnbBtcb",
]

runTestSetts = True

networkSettsMap = {
    "eth": settsToRun,
    "bsc": bscSettsToRun,
}
# NB: This is expected to fail if the network ID does not exist.
baseSettsToRun = networkSettsMap[network_manager.get_active_network()]

stabilizeSett = ["experimental.digg"]

stabilizeTestConfig = generate_sett_test_config(stabilizeSett, False)
settTestConfig = generate_sett_test_config(baseSettsToRun, runTestSetts)
diggSettTestConfig = generate_sett_test_config(diggSettsToRun, runTestSetts)
yearnSettTestConfig = generate_sett_test_config(yearnSettsToRun, runTestSetts)
clawSettTestConfig = generate_sett_test_config(clawSettsToRun, runTestSetts)
clawSettSyntheticTestConfig = generate_sett_test_config(
    clawSettsSytheticTestsToRun, runTestSetts
)


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


# @pytest.fixture()
def badger_single_sett(settConfig, deploy=True):
    if deploy:
        deployer = accounts[0]
        guardian = accounts[1]
        keeper = accounts[2]
        governance = accounts[4]
    else:
        with open(digg_config.prod_json) as f:
            badger_deploy = json.load(f)
            deployer = accounts.at(badger_deploy["deployer"], force=True)
            guardian = accounts.at(badger_deploy["guardian"], force=True)
            keeper = accounts.at(badger_deploy["keeper"], force=True)
            governance = accounts.at(badger_deploy["devMultisig"], force=True)

    strategist = accounts[3]

    settId = settConfig["id"]

    print("settId:", settId)

    if settConfig["mode"] == "test":
        if settId == "native.badger":
            return BadgerRewardsMiniDeploy(
                "native.badger",
                "StrategyBadgerRewards",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.renCrv":
            return CurveGaugeRenBtcMiniDeploy(
                "native.renCrv",
                "StrategyCurveGaugeRenBtcCrv",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sbtcCrv":
            return CurveGaugeSBtcMiniDeploy(
                "native.sbtcCrv",
                "StrategyCurveGaugeSbtcCrv",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.tbtcCrv":
            return CurveGaugeTBtcMiniDeploy(
                "native.tbtcCrv",
                "StrategyCurveGaugeTbtcCrv",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.uniBadgerWbtc":
            return BadgerLpMetaFarmMiniDeploy(
                "native.uniBadgerWbtc",
                "StrategyBadgerLpMetaFarm",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "harvest.renCrv":
            return HarvestMetaFarmMiniDeploy(
                "harvest.renCrv",
                "StrategyHarvestMetaFarm",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.unitRenBtc":
            return UnitProtocolRenBtcMiniDeploy(
                "native.unitRenBtc",
                "StrategyUnitProtocolRenbtc",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiBadgerWbtc":
            return SushiBadgerWBtcMiniDeploy(
                "native.sushiBadgerWbtc",
                "StrategySushiBadgerWbtc",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiWbtcEth":
            return SushiBadgerLpOptimizerMiniDeploy(
                "native.sushiWbtcEth",
                "StrategySushiLpOptimizer",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.digg":
            return DiggRewardsMiniDeploy(
                "native.digg",
                "StrategyDiggRewards",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(sett_type=SettType.DIGG, deploy=deploy)
        if settId == "native.uniDiggWbtc":
            return UniDiggWbtcLpMiniDeploy(
                "native.uniDiggWbtc",
                "StrategyDiggLpMetaFarm",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiDiggWbtc":
            return SushiDiggWbtcLpOptimizerMiniDeploy(
                "native.sushiDiggWbtc",
                "StrategySushiDiggWbtcLpOptimizer",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiSClawUSDC":
            # Claw/USDC mini deploy can be used for any CLAW synthetic token.
            return SushiClawUSDCMiniDeploy(
                "native.sushiSClawUSDC",
                "StrategySushiLpOptimizer",  # sushi lp optimizer strat is generic
                deployer,
                "sClaw",  # This specifies the name of the EMP contract on the CLAW system.
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiBClawUSDC":
            # Claw/USDC mini deploy can be used for any CLAW synthetic token.
            return SushiClawUSDCMiniDeploy(
                "native.sushiBClawUSDC",
                "StrategySushiLpOptimizer",  # sushi lp optimizer strat is generic
                deployer,
                "bClaw",  # This specifies the name of the EMP contract on the CLAW system.
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.pancakeBnbBtcb":
            return PancakeMiniDeploy.PancakeMiniDeploy(
                "native.pancakeBnbBtcb",
                "StrategyPancakeLpOptimzier",  # pancake lp optimizer strat is generic
                deployer,
                # Base strategy params (perf/withdrawal fees)
                sett_config.pancake.pancakeBnbBtcb,
                # Lp pair tokens (bnb/btcb) for this strategy.
                [registry.tokens.btcb, registry.tokens.bnb,],
                # Both want/pid are optional params and used for validation.
                # In this case, both the lp token and pid (pool id) exist so we can pass them in.
                want=registry.pancake.chefPairs.bnbBtcb,
                pid=registry.pancake.chefPids.bnbBtcb,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "native.sushiWbtcIbBtc":
            return SushiWbtcIbBtcLpOptimizerMiniDeploy(
                "native.sushiWbtcIbBtc",
                "StrategySushiLpOptimizer",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=True)  # Deploy for now since not already deployed.
        if settId == "native.uniWbtcIbBtc":
            return UniGenericLpMiniDeploy(
                "native.uniWbtcIbBtc",
                "StrategyUniGenericLp",
                deployer,
                [registry.tokens.ibbtc, registry.tokens.wbtc],
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=True)  # Deploy for now since not already deployed.
        if settId == "yearn.bvyWBTC":
            return YearnMiniDeploy(
                "yearn.bvyWBTC",
                "AffiliateTokenGatedUpgradable",
                deployer,
                strategist=strategist,
                guardian=guardian,
                keeper=keeper,
                governance=governance,
            ).deploy(deploy=deploy)
        if settId == "experimental.digg":
            return DiggStabilizeMiniDeploy().deploy(deploy=deploy)
    if settConfig['mode'] == 'prod':
        """
        Run vs prod contracts, transferring assets to the test user
        (WIP)
        """
        badger = connect_badger(badger_config.prod_json)

        distribute_test_ether(badger.deployer, Wei("20 ether"))
        distribute_from_whales(badger.deployer)

        return badger


@pytest.fixture(scope="function")
def badger_hunt_unit():
    deployer = accounts[0]
    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(deployer)

    badger.deploy_logic("BadgerHunt", BadgerHunt)
    badger.deploy_badger_hunt()

    source = accounts.at("0x394DCfbCf25C5400fcC147EbD9970eD34A474543", force=True)

    badger.token.transfer(badger.badgerHunt, Wei("100000 ether"), {"from": source})

    return badger


@pytest.fixture(scope="function")
def badger_tree_unit():
    deployer = accounts[0]
    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(deployer)

    badger.deploy_logic("BadgerHunt", BadgerHunt)
    badger.deploy_badger_hunt()

    badger.token.transfer(
        badger.badgerHunt, badger_config.huntParams.badgerAmount, {"from": deployer}
    )

    return badger


@pytest.fixture(scope="function")
def digg_distributor_unit():
    badger = connect_badger(badger_config.prod_json)
    deployer = badger.deployer
    devProxyAdminAddress = badger.devProxyAdmin.address
    daoProxyAdminAddress = badger.daoProxyAdmin.address
    digg = deploy_digg_minimal(
        deployer, devProxyAdminAddress, daoProxyAdminAddress, owner=deployer
    )

    # deployer should have eth but just in case
    distribute_test_ether(badger.deployer, Wei("20 ether"))

    digg.deploy_airdrop_distributor(
        digg_config.airdropRoot,
        badger.rewardsEscrow,
        digg_config.reclaimAllowedTimestamp,
    )

    totalSupply = digg.token.totalSupply()
    # 15% airdropped
    digg.token.transfer(digg.diggDistributor, totalSupply * 0.15, {"from": deployer})

    return digg


@pytest.fixture(scope="function")
def digg_distributor_prod_unit():
    badger = connect_badger(
        "deploy-final.json", load_deployer=True, load_keeper=True, load_guardian=True
    )
    digg = connect_digg("deploy-final.json")
    digg.token = digg.uFragments

    badger.add_existing_digg(digg)
    init_prod_digg(badger, badger.deployer)
    return digg


@pytest.fixture()
def badger(accounts):
    badger_system = deploy_flow(test=True, outputToFile=False)

    # Distribute Test Assets
    return badger_system


@pytest.fixture()
def badger_prod(accounts):
    badger_system = deploy_flow(test=True, outputToFile=True, uniswap=False)

    # Distribute Test Assets
    return badger_system
