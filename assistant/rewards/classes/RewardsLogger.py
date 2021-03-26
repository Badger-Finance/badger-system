from tabulate import tabulate
from rich.console import Console
from assistant.rewards.aws_utils import upload_analytics
import json

console = Console()
class RewardsLogger:
    def __init__(self):
        self._unlockSchedules = {}
        self._userData = {}
        self._merkleRoot = ""

    def set_merkle_root(self,root):
        self._merkleRoot = root

    def _check_user_vault(self,address,vault):
        if vault not in self._userData:
            self._userData[vault] = {}
        if address not in self._userData[vault]:
            self._userData[vault][address] = {}

    def add_user_token(self,address,vault,token,tokenAmount):
        self._check_user_vault(address,vault)
        if "totals" not in self._userData[vault][address]:
            self._userData[vault][address]["totals"] = {}
        if token not in self._userData[vault][address]["totals"]:
            self._userData[vault][address]["totals"][token] = tokenAmount
        else:
            self._userData[vault][address]["totals"][token] += tokenAmount

    def add_multiplier(self,address,vault,multiplier):
        self._check_user_vault(address,vault)
        self._userData[vault][address]["multiplier"] = multiplier

    def add_unlock_schedules(self,name,token,schedule):
        if name not in self._unlockSchedules:
            self._unlockSchedules[name] = {}
        else:   
            self._unlockSchedules[name][token] = schedule


    def save(self,fileName):

        data = {
            "merkleRoot": self._merkleRoot,
            "userData":self._userData,
            "unlockSchedules":self._unlockSchedules,
        }
        upload_analytics(fileName,data)
        with open("logs/{}.json".format(fileName),"w") as f:
            json.dump(data,f,indent=4)


rewardsLogger = RewardsLogger()