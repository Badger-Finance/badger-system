from enum import Enum
from brownie import rpc, network

class NetworkManager():
    def is_forknet(self):
        return rpc.is_active()
    def get_active_network(self):
        active_network = network.show_active()
        print(active_network)
        return "bsc" # TODO: This is not working with brownie test - it does not read the network data
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
            return "badger-test-bsc.json"
        else:
            raise Exception("No badger deploy file registered for network {}".format(active))

network_manager = NetworkManager()