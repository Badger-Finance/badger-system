from rich.console import Console
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from helpers.constants import BADGER, DIGG
import numpy as np
import json

console = Console()


class RewardsLog:
    def __init__(self):
        self._unlockSchedules = {}
        self._userData = {}
        self._totalTokenDist = {}
        self._merkleRoot = ""
        self._diggAllocation = 0

    def set_merkle_root(self, root):
        self._merkleRoot = root

    def add_total_token_dist(self, name, token, amount):
        if name not in self._totalTokenDist:
            self._totalTokenDist[name] = {}
        self._totalTokenDist[name][token] = amount

    def _check_user_vault(self, address, vault):
        if vault not in self._userData:
            self._userData[vault] = {}
        if address not in self._userData[vault]:
            self._userData[vault][address] = {}

    def add_user_token(self, address, vault, token, tokenAmount):
        self._check_user_vault(address, vault)
        if "totals" not in self._userData[vault][address]:
            self._userData[vault][address]["totals"] = {}
        if token not in self._userData[vault][address]["totals"]:
            self._userData[vault][address]["totals"][token] = tokenAmount
        else:
            self._userData[vault][address]["totals"][token] += tokenAmount

    def add_multiplier(self, address, vault, multiplier):
        self._check_user_vault(address, vault)
        self._userData[vault][address]["multiplier"] = multiplier

    def add_unlock_schedules(self, name, token, schedule):
        if name not in self._unlockSchedules:
            self._unlockSchedules[name] = {}
        else:
            self._unlockSchedules[name][token] = schedule

    def save(self, fileName):

        data = {
            "merkleRoot": self._merkleRoot,
            "userData": self._userData,
            "unlockSchedules": self._unlockSchedules,
            "totalTokenDist": self._totalTokenDist,
        }
        width = 0.4
        x_axis = []
        for name in self._totalTokenDist.keys():
            settName = name.split(".")
            if settName[0] == "harvest":
                x_axis.append("hrenBtc")
            else:
                x_axis.append(settName[1])

        badger_emissions = []
        digg_emissions = []
        for sett, emissions in self._totalTokenDist.items():
            if BADGER in emissions:
                badger_emissions.append(emissions[BADGER])
            else:
                badger_emissions.append(0)
            if DIGG in emissions:
                digg_emissions.append(emissions[DIGG])
            else:
                digg_emissions.append(0)

        bar1 = np.arange(len(x_axis))
        bar2 = [i + width for i in bar1]
        fig, ax = plt.subplots()
        ax2 = ax.twinx()
        ax.set_ylim([0, max(badger_emissions) * 1.2])
        ax2.set_ylim([0, max(digg_emissions) * 1.2])

        ax.bar(
            bar1,
            badger_emissions,
            width,
            label="Badger",
            color="grey",
            edgecolor="black",
        )
        ax2.bar(
            bar2, digg_emissions, width, label="Digg", color="orange", edgecolor="black"
        )
        ax.set_ylabel("Badger distributed")
        ax2.set_ylabel("Digg distributed")
        ax.yaxis.set_major_locator(ticker.MultipleLocator(base=5.0))
        # ax2.yaxis.set_major_locator(ticker.MultipleLocator(base=0.25/1e11))

        plt.title("Tokens distributed as rewards per cycle")
        plt.xticks(bar1 + width / 2, x_axis)
        plt.xticks(rotation=70)
        plt.tick_params(axis="x", which="minor", labelsize=12)
        ax.legend(loc="upper left")
        ax2.legend(loc="upper right")
        ax.tick_params(axis="x", rotation=70)
        fig.set_size_inches(13.875, 7.875)

        plt.tight_layout()

        plt.savefig("logs/rewards/{}.png".format(fileName), dpi=150)

        with open("logs/rewards/{}.json".format(fileName), "w") as f:
            json.dump(data, f, indent=4)


rewardsLog = RewardsLog()
