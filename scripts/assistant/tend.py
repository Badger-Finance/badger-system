from brownie import *
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

from assistant.rewards.rewards_checker import val

console = Console()


def tend_all(badger: BadgerSystem, test, skip):
    keeper = badger.deployer
    table = []
    for key, vault in badger.sett_system.vaults.items():
        if key in skip:
            continue

        strategy = badger.getStrategy(key)
        if not strategy.isTendable():
            continue
        console.print("\n[bold green]===== Tend: " + key + " =====[/bold green]\n")
        fpps_before = vault.getPricePerFullShare()

        if test:
            chain.mine()

        print("Tend: " + key)
        check_tend(vault, strategy, keeper)

        if test:
            chain.mine()

        table.append(
            [
                key,
                val(fpps_before),
                val(vault.getPricePerFullShare()),
                val(vault.getPricePerFullShare() - fpps_before),
            ]
        )

        print("PPFS: Tend")
        print(tabulate(table, headers=["name", "before", "after", "diff"]))

def main():
    """
    Simulate tend operation and evaluate tendable amount
    """
    test = False
    tend = True

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    # keeper = badger.keeper

    user = ""

    # Give tester Sett tokens
    if test:
        user = accounts[5]
        print("Claiming from Whales...")
        claim_assets_from_whales(badger, user)

    # TODO Load keeper account from file

    # skip = ["harvest.renCrv"]
    skip = [
        # "native.uniBadgerWbtc"
        # "harvest.renCrv",
        "native.sbtcCrv",
        "native.sBtcCrv",
        "native.tbtcCrv",
        "native.renCrv",
        # "native.badger",
    ]
    if earn:
        earn_all(badger, test, user, skip)
    if tend:
        tend_all(badger, test, skip)
    if harvest:
        harvest_all(badger, test, skip)

    # for i in range(0,1):
    #     chain.sleep(hours(12))
    #     chain.mine()
    #     tend_all(badger, test, skip)
    #     chain.mine()

    # harvest_all(badger, test, skip)

    # chain.sleep(hours(24))
    # chain.mine()
    # tend_all(badger, test, skip)

    # chain.mine()
    # harvest_all(badger, test, skip)

    # if harvest:
    #     harvest_all(badger, test, skip)

    if test:
        withdraw_sim(badger, test, user, skip)
