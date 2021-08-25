from helpers.time_utils import days, to_utc_date
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.console_utils import console


class BadgerRewardsManagerHelper:
    def __init__(self, badger, helper):
        self.badger = badger
        self.helper = helper

    def approve_strategies_on_rewards_manager(self, strategy_keys):
        rm = self.helper.contract_from_abi(
            self.badger.badgerRewardsManager.address,
            "BadgerRewardsManager",
            BadgerRewardsManager.abi,
        )
        for key in strategy_keys:
            strat = self.badger.getStrategy(key)
            console.print(
                f"Approving Strategy for keeping activities {key} {strat.address} on RewardsManager"
            )
            rm.grantRole(APPROVED_STRATEGY_ROLE, strat)
            rm.approveStrategy(strat)

    def approve_setts_on_rewards_manager(self, sett_keys):
        rm = self.helper.contract_from_abi(
            self.badger.badgerRewardsManager.address,
            "BadgerRewardsManager",
            BadgerRewardsManager.abi,
        )
        for key in sett_keys:
            sett = self.badger.getSett(key)
            console.print(
                f"Granting role {APPROVED_SETT_ROLE} to Sett {key} {sett.address} on RewardsManager"
            )
            rm.grantRole(APPROVED_SETT_ROLE, sett)

    def grant_role_on_rewards_manager(self, ROLE, addresses):
        rm = self.helper.contract_from_abi(
            self.badger.badgerRewardsManager.address,
            "BadgerRewardsManager",
            BadgerRewardsManager.abi,
        )
        for address in addresses:
            console.print(f"Granting role {ROLE} to {address} on RewardsManager")
            rm.grantRole(ROLE, address)
            assert rm.hasRole(ROLE, address)

    def revoke_role_on_rewards_manager(self, ROLE, addresses):
        rm = self.helper.contract_from_abi(
            self.badger.badgerRewardsManager.address,
            "BadgerRewardsManager",
            BadgerRewardsManager.abi,
        )
        for address in addresses:
            console.print(f"Granting role {ROLE} to {address} on RewardsManager")
            rm.revokeRole(ROLE, address)
            assert not rm.hasRole(ROLE, address)
