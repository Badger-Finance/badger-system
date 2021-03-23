from enum import Enum
from brownie import rpc, network, config
from helpers.console_utils import console
import sys

class NetworkManager():


    def is_forknet(self):
        return rpc.is_active()


    def network_name(self, s):
        if s == None:
            return None
        if "mainnet" in s:
            return "eth"
        if "bsc" in s or "binance-fork" in s:
            return "bsc"
        return None


    def get_active_network(self):
        active_network = network.show_active()
        return "bsc"
        console.print("[cyan]🖲  Active network: {}[/cyan]".format(active_network))

        if active_network == None:
            name = self.network_name(sys.argv)
        else:
            name = self.network_name(active_network)

        if name:
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
            raise Exception("No badger deploy file registered for network {}".format(active))


network_manager = NetworkManager()