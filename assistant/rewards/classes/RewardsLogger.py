from tabulate import tabulate
from rich.console import Console
from assistant.rewards.aws_utils import upload_analytics
import json

console = Console()
class RewardsLogger:
    def __init__(self):
        self._unlockSchedules = {}
        self._userData = {}
<<<<<<< HEAD:assistant/rewards/classes/RewardsLogger.py
        self._merkleRoot = ""

    def set_merkle_root(self,root):
        self._merkleRoot = root
=======
        self._epochData = {}
        self._metadata = {}

>>>>>>> origin/peg-rewards:assistant/rewards/RewardsLogger.py

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

<<<<<<< HEAD:assistant/rewards/classes/RewardsLogger.py
    def add_unlock_schedules(self,name,token,schedule):
        if name not in self._unlockSchedules:
            self._unlockSchedules[name] = {}
        else:   
            self._unlockSchedules[name][token] = schedule

=======
    def add_metadata(self,key,value):
        self._metadata[key] = value

    def add_unlock_schedule(self,token,schedule):
        self._unlockSchedules[token] = schedule

    def add_distribution_info(self,geyserName,distribution):
        self._distributionInfo[geyserName] = distribution
>>>>>>> origin/peg-rewards:assistant/rewards/RewardsLogger.py

    def save(self,fileName):

        data = {
            "merkleRoot": self._merkleRoot,
            "userData":self._userData,
            "unlockSchedules":self._unlockSchedules,
<<<<<<< HEAD:assistant/rewards/classes/RewardsLogger.py
=======
            "retroactiveData":self._epochData,
            "metadata":self._metadata
>>>>>>> origin/peg-rewards:assistant/rewards/RewardsLogger.py
        }
        upload_analytics(fileName,data)
        with open("logs/{}.json".format(fileName),"w") as f:
            json.dump(data,f,indent=4)


rewardsLogger = RewardsLogger()