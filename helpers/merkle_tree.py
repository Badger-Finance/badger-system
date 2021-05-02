from assistant.rewards.RewardsList import RewardsList
from itertools import zip_longest

from brownie import *
from eth_utils import encode_hex
from eth_utils.hexadecimal import encode_hex
from helpers.constants import *
from helpers.console_utils import console


class MerkleTree:
    def __init__(self, elements):
        for el in elements:
            print(el)
            print(len(el))
            el = encode_hex(el)
            print(el)
            print(type(el))
            break
        self.elements = sorted(set(web3.keccak(hexstr=el) for el in elements))
        self.layers = MerkleTree.get_layers(self.elements)

        # console.log(self.elements, self.layers)

    @property
    def root(self):
        return self.layers[-1][0]

    def get_proof(self, el):
        el = web3.keccak(hexstr=el)
        idx = self.elements.index(el)
        proof = []
        for layer in self.layers:
            pair_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if pair_idx < len(layer):
                proof.append(encode_hex(layer[pair_idx]))
            idx //= 2
        return proof

    @staticmethod
    def get_layers(elements):
        layers = [elements]
        while len(layers[-1]) > 1:
            layers.append(MerkleTree.get_next_layer(layers[-1]))
        return layers

    @staticmethod
    def get_next_layer(elements):
        return [
            MerkleTree.combined_hash(a, b)
            for a, b in zip_longest(elements[::2], elements[1::2])
        ]

    @staticmethod
    def combined_hash(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return web3.keccak(b"".join(sorted([a, b])))


def rewards_to_merkle_tree(rewards: RewardsList, startBlock, endBlock, geyserRewards):
    (nodes, encodedNodes, entries) = rewards.to_merkle_format()

    # For each user, encode their data into a node

    # Put the nodes into a tree

    # elements = [(index, account, amount) for index, (account, amount) in enumerate(rewards.items())]
    # nodes = [encode_hex(encode_abi_packed(['uint', 'address', 'uint'], el)) for el in elements]
    """
    'claims': {
            user: {'index': index, 'amount': hex(amount), 'proof': tree.get_proof(nodes[index])}
            for index, user, amount in elements
        },
    """
    tree = MerkleTree(encodedNodes)
    distribution = {
        "merkleRoot": encode_hex(tree.root),
        "cycle": nodes[0]["cycle"],
        "startBlock": str(startBlock),
        "endBlock": str(endBlock),
        "tokenTotals": rewards.totals.toDict(),
        "claims": {},
        "metadata": {},
    }

    for entry in entries:
        node = entry["node"]
        encoded = entry["encoded"]
        # console.log(node)
        distribution["claims"][node["user"]] = {
            "index": hex(node["index"]),
            "user": node["user"],
            "cycle": hex(node["cycle"]),
            "tokens": node["tokens"],
            "cumulativeAmounts": node["cumulativeAmounts"],
            "proof": tree.get_proof(encodedNodes[node["index"]]),
            "node": encoded,
        }
    if len(geyserRewards) > 0:
        for user, data in geyserRewards.metadata.items():
            distribution["metadata"][user] = data.toDict()

    print(f"merkle root: {encode_hex(tree.root)}")

    # Print to file with content hash
    # hash(distribution)

    # console.log(distribution)

    return distribution
