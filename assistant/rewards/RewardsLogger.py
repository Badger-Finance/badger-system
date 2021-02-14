from tabulate import tabulate
from rich.console import Console
import json
console = Console()
class RewardsLogger:
    def __init__(self):
        self._distributionInfo = {}
        self._unlockSchedules = {}
        self._userData = {}
        self._epochData = {}

    def _check_user_vault(self,address,vault):
        if vault not in self._userData:
            self._userData[vault] = {}
        if address not in self._userData[vault]:
            self._userData[vault][address] = {}


    def add_epoch_data(self,users,vault,token,unit,epoch):
        if vault not in self._epochData:
            self._epochData[vault] = {}
        if epoch not in self._epochData[vault]:
            self._epochData[vault][epoch] = {}
        for user in users:
            totals = {}
            totals[token] = unit * user.shareSeconds
            self._epochData[vault][epoch][user.address] = {
                "shareSeconds":user.shareSeconds,
                "totals":totals
            }

    

    def add_user_share_seconds(self,address,vault,shareSeconds):
        self._check_user_vault(address,vault)
        if "shareSeconds" not in self._userData[vault][address]:
            self._userData[vault][address]["shareSeconds"] = shareSeconds
        else:
            self._userData[vault][address]["shareSeconds"] += shareSeconds

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

    def add_unlock_schedule(self,token,schedule):
        self._unlockSchedules[token] = schedule

    def add_distribution_info(self,geyserName,distribution):
        self._distributionInfo[geyserName] = distribution




    def save(self,fileName):

        data = {
            "userData":self._userData,
            "distributionInfo":self._distributionInfo,
            "unlockSchedules":self._unlockSchedules,
            "retroactiveData":self._epochData
        }
        with open("logs/{}.json".format(fileName),"w") as f:
            json.dump(data,f,indent=4)
    


rewardsLogger = RewardsLogger()