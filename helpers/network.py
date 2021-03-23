from enum import Enum
from brownie import rpc, network, config
from helpers.console_utils import console

class NetworkManager():
    def is_forknet(self):
        return rpc.is_active()
    def get_active_network(self):
        active_network = network.show_active()
        return "bsc"
        console.print("[cyan]🖲  Active network: {}[/cyan]".format(active_network))
        if "mainnet" in active_network:
            return "eth"
        if "bsc" in active_network:
            return "bsc"
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
            raise Exception("No badger deploy file registered for network {}".format(active))

network_manager = NetworkManager()