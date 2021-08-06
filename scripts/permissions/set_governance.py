from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from ape_safe import ApeSafe

def main():
    badger = connect_badger()
    multi = badger.opsMultisig
    safe = ApeSafe(multi.address)
    helper = ApeSafeHelper(badger, safe)

    gov = badger.governanceTimelock

    for sett_id in badger.getAllSettIds():
        if sett_id in ["yearn.wbtc"]:
            continue

        sett = helper.contract_from_abi(
            badger.getSett(sett_id).address, "SettV3", SettV3.abi
        )
        strategy = helper.contract_from_abi(
            badger.getStrategy(sett_id).address, "StrategyCvxCrvHelper", StrategyCvxCrvHelper.abi
        )

        console.print(
            {
                "key": sett_id,
                "sett governance": sett.governance(),
                "strategy governance": strategy.governance(),
            }
        )

        if sett.governance() == multi:
            sett.setGovernance(gov)
            assert sett.governance() == gov
            
        if strategy.governance() == multi:
            strategy.setGovernance(gov)
            assert strategy.governance() == gov

    helper.publish()
