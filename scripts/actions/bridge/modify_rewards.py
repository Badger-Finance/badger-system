from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.bridge_system import BridgeSystem, connect_bridge
from config.badger_config import badger_config

console = Console()

# Equal percentage fee bps for both governance/rewards
PERCENTAGE_FEE_BPS = 5000


def modify_rewards(badger: BadgerSystem, bridge: BridgeSystem):
    multisig = GnosisSafe(badger.devMultisig)
    multisig.execute(
        MultisigTxMetadata(description="update rewards split governance"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setPercentageFeeGovernanceBps.encode_input(PERCENTAGE_FEE_BPS),
        },
    )
    multisig.execute(
        MultisigTxMetadata(description="update rewards split rewards"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setPercentageFeeRewardsBps.encode_input(PERCENTAGE_FEE_BPS),
        },
    )


def main():
    """
    Connect to badger system, and configure rewards split on bridge contract.
    """

    # Connect badger system from file
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    modify_rewards(badger, bridge)
