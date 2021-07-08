import datetime
import json
import os
import time
import warnings

import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import initial_fragments_to_current_fragments, val
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.token_utils import asset_to_address

console = Console()
pretty.install()


class GeyserDistributor:
    """
    Generate geyser distribution transactions given a set of emissions
    """

    def generate(self, badger, multi, key, distributions, start=0, duration=0, end=0):
        dists = []
        for asset, dist in distributions.items():
            if dist == 0:
                continue
            console.print(
                "===== Distributions for asset {} on {} =====".format(asset, key),
                style="bold yellow",
            )

            token = asset_to_address(asset)

            # == Distribute to Geyser ==
            geyser = badger.getGeyser(key)
            rewardsEscrow = badger.rewardsEscrow
            multi = GnosisSafe(badger.devMultisig)
            opsMulti = GnosisSafe(badger.opsMultisig)

            print(key, geyser, rewardsEscrow)

            if rewardsEscrow.isApproved(geyser) == False:
                multi.execute(
                    MultisigTxMetadata(description="Approve Recipient"),
                    {
                        "to": rewardsEscrow.address,
                        "data": rewardsEscrow.approveRecipient.encode_input(geyser),
                    },
                )

            # Approve Geyser as recipient if required
            if not rewardsEscrow.isApproved(geyser):
                multi.execute(
                    MultisigTxMetadata(
                        description="Approve StakingRewards " + key,
                        operation="transfer",
                    ),
                    {
                        "to": rewardsEscrow.address,
                        "data": rewardsEscrow.approveRecipient.encode_input(geyser),
                    },
                )

            numSchedules = geyser.unlockScheduleCount(token)
            console.print(
                "Geyser Distribution for {}: {}".format(key, val(dist)), style="yellow",
            )

            dists.append((geyser, asset_to_address(asset), dist, duration, start))

        console.log(key, dists)
        return dists
