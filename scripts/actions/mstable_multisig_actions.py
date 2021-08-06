from brownie import MStableVoterProxy
from helpers.registry import registry
from scripts.systems.badger_system import connect_badger
from ape_safe import ApeSafe
from helpers.gnosis_safe import ApeSafeHelper


def main():
    supportStrategies()


def supportStrategies():
    badger = connect_badger("deploy-final.json")

    # Get mStable-Badger dualGovernance account from VoterProxy
    voterproxy = MStableVoterProxy.at("0x10D96b1Fd46Ce7cE092aA905274B8eD9d4585A6E")
    # Get mStable-Badger dualGovernance account from VoterProxy
    dualGovernance = voterproxy.governance()
    assert dualGovernance == "0xCa045cC466f14C33a516D98abcab5C55C2f5112c"

    safe = ApeSafe(dualGovernance)
    helper = ApeSafeHelper(badger, safe)

    # Check that strategies have not yet been supported on VoterProxy
    mstableImBtcStrat = badger.getStrategy("native.mstableImBtc")
    mstableFpMbtcHbtcStrat = badger.getStrategy("native.mstableFpMbtcHbtc")

    print("mstableImBtcStrat address: ", mstableImBtcStrat.address)
    print("mstableFpMbtcHbtcStrat address: ", mstableFpMbtcHbtcStrat.address)

    # Strategies are already supported
    # assert voterproxy.strategyToVault(mstableImBtcStrat.address) == "0x0"
    # assert voterproxy.strategyToVault(mstableFpMbtcHbtcStrat.address) == "0x0"

    # Get mStable vaults
    imBtcVault = registry.mstable.pools.imBtc.vault
    fPmBtcHBtcVault = registry.mstable.pools.fPmBtcHBtc.vault

    # Support Strategies
    destination = helper.contract_from_abi(
        voterproxy.address, "MStableVoterProxy", MStableVoterProxy.abi
    )

    destination.supportStrategy(mstableImBtcStrat.address, imBtcVault)
    destination.supportStrategy(mstableFpMbtcHbtcStrat.address, fPmBtcHBtcVault)

    helper.publish()
