from enum import Enum
from brownie import rpc, network

class Chains(Enum):
    ETH = 'eth',
    BSC = 'bsc',
    FTM = 'ftm',
    MATIC = 'matic'

class NetworkManager():
    def is_forknet(self):
        return rpc.is_active()
    def get_active_network(self):
        active_network = network.show_active()
        if 'mainnet' in active_network:
            return Chains.ETH
        else:
            return active_network

network_manager = NetworkManager()