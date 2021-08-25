from helpers.time_utils import days
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256

from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from helpers.gnosis_safe import ApeSafeHelper
from ape_safe import ApeSafe


class GovernanceTimelockParams:
    def __init__(self, target="", value=0, signature="", data="", eta=0):
        self.target = target
        self.value = value
        self.signature = signature
        self.data = data

        if eta == 0:
            # Set ETA automatically
            self.eta = chain.time() + days(3)
        else:
            self.eta = eta


def main():
    badger = connect_badger()
    multi = badger.devMultisig
    safe = ApeSafe(multi.address)
    helper = ApeSafeHelper(badger, safe)

    kac = interface.IAccessControl("0x711A339c002386f9db409cA55b6A35a604aB6cF6")
    test = False

    for sett_id in badger.getAllSettIds():
        if sett_id in ["yearn.wbtc"]:
            continue

        sett = helper.contract_from_abi(
            badger.getSett(sett_id).address, "SettV3", SettV3.abi
        )
        strategy = helper.contract_from_abi(
            badger.getStrategy(sett_id).address,
            "StrategyCvxCrvHelper",
            StrategyCvxCrvHelper.abi,
        )

        timelock = helper.contract_from_abi(
            badger.governanceTimelock.address,
            "GovernanceTimelock",
            GovernanceTimelock.abi,
        )

        assert sett.address != strategy.address

        console.print(
            {
                "key": sett_id,
                "sett governance": sett.governance(),
                "strategy governance": strategy.governance(),
            }
        )

        if sett.governance() == badger.governanceTimelock:
            params = GovernanceTimelockParams(
                target=sett.address,
                signature="setKeeper(address)",
                data=sett.setKeeper.encode_input(kac.address),
            )

            print(params)
            timelock.queueTransaction(
                params.target,
                params.value,
                params.signature,
                params.data,
                params.eta,
            )

            if test:
                chain.mine()
                chain.sleep(days(4))
                chain.mine()
                print(params)
                sett.setKeeper(kac, {"from": tl})
                # tx = timelock.executeTransaction(
                #     params.target,
                #     params.value,
                #     params.signature,
                #     params.data,
                #     params.eta,
                # )
                assert sett.keeper() == kac

        if strategy.governance() == badger.governanceTimelock:
            params = GovernanceTimelockParams(
                target=strategy.address,
                signature="setKeeper(address)",
                data=strategy.setKeeper.encode_input(kac),
            )

            timelock.queueTransaction(
                params.target,
                params.value,
                params.signature,
                params.data,
                params.eta,
            )

            if test:
                tl = accounts.at(timelock.address, force=True)
                chain.mine()
                chain.sleep(days(4))
                chain.mine()
                print(params)
                strategy.setKeeper(kac, {"from": tl})
                # tx = timelock.executeTransaction(
                #     params.target,
                #     params.value,
                #     params.signature,
                #     params.data,
                #     params.eta,
                # )
                assert strategy.keeper() == kac

    helper.publish()
