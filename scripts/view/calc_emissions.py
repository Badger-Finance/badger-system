from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.utils import shares_to_fragments, val
from brownie import *
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from config.badger_config import badger_config
from config.active_emissions import get_active_rewards_schedule


def main():
    badger = connect_badger(badger_config.prod_json)
    rewards = get_active_rewards_schedule(badger)

    b1 = (
        rewards.getDistributions("native.uniBadgerWbtc").getToStakingRewardsDaily(
            "badger"
        )
        * 5
    )
    b2 = (
        rewards.getDistributions("native.sushiBadgerWbtc").getToStakingRewardsDaily(
            "badger"
        )
        * 5
    )
    b3 = (
        rewards.getDistributions("native.badger").getToStakingRewardsDaily("badger") * 5
    )

    total_badger = b1 + b2 + b3

    d1 = (
        shares_to_fragments(
            rewards.getDistributions("native.uniDiggWbtc").getToStakingRewardsDaily(
                "digg"
            )
        )
        * 5
    )
    d2 = (
        shares_to_fragments(
            rewards.getDistributions("native.sushiDiggWbtc").getToStakingRewardsDaily(
                "digg"
            )
        )
        * 5
    )
    d3 = (
        shares_to_fragments(
            rewards.getDistributions("native.digg").getToStakingRewardsDaily("digg")
        )
        * 6
    )

    total_digg = d1 + d2 + d3

    table = []
    table.append(["native.uniBadgerWbtc", val(b1)])
    table.append(["native.sushiBadgerWbtc", val(b2)])
    table.append(["native.badger", val(b3)])
    table.append(["total badger", val(total_badger)])
    print(tabulate(table, headers=["metric", "value"]))

    table = []
    table.append(["native.uniDiggWbtc", val(d1, decimals=9)])
    table.append(["native.sushiDiggWbtc", val(d2, decimals=9)])
    table.append(["native.digg", val(d3, decimals=9)])
    table.append(["total digg", val(total_digg, decimals=9)])
    print(tabulate(table, headers=["metric", "value"]))

    rewards.printState("Geyser Emissions")

    # Generate Sufficient
    multi = GnosisSafe(badger.devMultisig)

    print(badger.badgerRewardsManager)

    multi.execute(
        MultisigTxMetadata(description="Transfer Remaining Weekly Badger"),
        {
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                badger.token, badger.badgerRewardsManager, total_badger
            ),
        },
    )

    assert badger.token.balanceOf(badger.badgerRewardsManager) >= total_badger

    multi.execute(
        MultisigTxMetadata(description="Transfer Remaining Weekly Badger"),
        {
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                badger.digg.token, badger.badgerRewardsManager, total_digg
            ),
        },
    )

    assert badger.digg.token.balanceOf(badger.badgerRewardsManager) >= total_digg
