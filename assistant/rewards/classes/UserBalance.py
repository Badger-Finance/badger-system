from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class UserBalance:
    address: str
    balance: int
    token: str
    type: List[str] = field(default_factory=lambda: [])

    def boost_balance(self, boost):
        self.balance = self.balance * boost


@dataclass
class UserBalances:
    userBalances: Dict[str, UserBalance] = field(default_factory=lambda: [])

    def __post_init__(self):
        if len(self.userBalances) > 0:
            self.userBalances = {u.address: u for u in self.userBalances}
        else:
            self.userBalances = {}

    def total_balance(self):
        return sum([u.balance for u in self.userBalances.values()])

    def percentage_of_total(self, addr):
        return self[addr].balance / self.total_balance()

    def __getitem__(self, key):
        return self.userBalances.get(key, None)

    def __setitem__(self, key, value):
        self.userBalances[key] = value

    def __contains__(self, key):
        return key in self.userBalances

    def __add__(self, other):
        newUserBalances = self.userBalances
        for user in other.userBalances.values():
            if user.address in newUserBalances:
                newUserBalances[user.address].balance += user.balance
            else:
                newUserBalances[user.address] = user
        return UserBalances(newUserBalances.values())

    def __iter__(self):
        for user in self.userBalances.values():
            yield user

    def __len__(self):
        return len(self.userBalances)
