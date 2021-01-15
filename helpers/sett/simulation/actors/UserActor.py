from brownie import Sett
from typing import Any

from helpers.constants import MaxUint256
from helpers.sett.SnapshotManager import SnapshotManager
from .BaseAction import BaseAction


class DepositAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        user: Any,
        sett: Sett,
        want: Any,
    ):
        self.snap = snap
        self.user = user
        self.want = want
        self.sett = sett

    def run(self):
        user = self.user
        want = self.want

        startingBalance = want.balanceOf(user)
        depositAmount = startingBalance // 2
        assert startingBalance >= depositAmount
        assert startingBalance >= 0

        want.approve(
            self.sett,
            MaxUint256,
            {"from": user},
        )
        self.snap.settDeposit(
            depositAmount,
            {"from": user},
        )


class WithdrawAction(BaseAction):
    def __init__(
        self,
        snap: SnapshotManager,
        user: Any,
    ):
        self.snap = snap
        self.user = user

    def run(self):
        self.snap.settWithdrawAll({"from": self.user})


class UserActor:
    def __init__(self, manager: Any, user: Any):
        self.snap = manager.snap
        self.sett = manager.sett
        self.want = manager.want
        self.user = user
        self.deposited = False

    def generateAction(self) -> BaseAction:
        '''
        Only produce deposit -> withdraw -> deposit -> withdraw...
        operations for now. May add support for interleaving ops
        at a later time.
        '''
        if self.deposited:
            self.deposited = False
            return WithdrawAction(
                self.snap,
                self.user,
            )
        self.deposited = True
        return DepositAction(
            self.snap,
            self.user,
            self.sett,
            self.want,
        )
