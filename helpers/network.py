from enum import Enum
from brownie import rpc, network, config
from helpers.console_utils import console
import re
import sys


class NetworkManager:
    def is_forknet(self):
        return rpc.is_active()

    def network_name(self, s):
        if re.match(r"^mainnet", s):
            return "eth"
        if re.match(r"(?:bsc|binance)", s):
            return "bsc"
        return None

    def get_active_network(self):
        active_network = network.show_active()
        # return "bsc"
        name = None

        if active_network == None:
            if "--network" not in sys.argv:
                console.print(
                    "Network not found, defaulting to 'eth' (did you set the --network flag?)"
                )
                name = "eth"
            else:
                network_idx = sys.argv.index("--network")
                name = self.network_name(sys.argv[network_idx + 1])
        else:
            name = self.network_name(active_network)

        if name:
            console.print("[cyan]🖲  Active network: {}[/cyan]".format(name))
            return name
        else:
            raise Exception("Chain ID {} not recognized".format(active_network))

    def get_active_network_badger_deploy(self):
        active = self.get_active_network()
        if active == "eth":
            return "deploy-final.json"
        elif active == "bsc":
            return "badger-deploy-bsc.json"
            # return "badger-test-bsc.json"
        else:
            raise Exception(
                "No badger deploy file registered for network {}".format(active)
            )


network_manager = NetworkManager()
