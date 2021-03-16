from brownie import *
from dotmap import DotMap
from rich.console import Console
from eth_utils.hexadecimal import encode_hex
from eth_abi import decode_single, encode_single, encode_abi
from eth_abi.packed import encode_abi_packed
from tabulate import tabulate

console = Console()


class RewardsList:
    def __init__(self, cycle, badgerTree) -> None:
        self.claims = DotMap()
        self.tokens = DotMap()
        self.totals = DotMap()
        self.boost = DotMap()
        self.cycle = cycle
        self.badgerTree = badgerTree
        self.metadata = DotMap()
        self.sources = DotMap()
        self.sourceMetadata = DotMap()

    def increase_user_rewards_source(self, source, user, token, toAdd):
        if not self.sources[source][user][token]:
            self.sources[source][user][token] = 0
        self.sources[source][user][token] += toAdd

    def track_user_metadata_source(self, source, user, metadata):
        if not self.sourceMetadata[source][user][metadata]:
            self.sourceMetadata[source][user][metadata] = DotMap()
        self.sourceMetadata[source][user][metadata] = metadata
    
    def add_user_boost(self,user,boostAmount):
        self.boost[user] = boostAmount

    def increase_user_rewards(self, user, token, toAdd):
        if toAdd < 0:
            print("NEGATIVE to ADD")
            toAdd = 0

        """
        If user has rewards, increase. If not, set their rewards to this initial value
        """
        if user in self.claims and token in self.claims[user]:
            self.claims[user][token] += toAdd
        else:
            self.claims[user][token] = toAdd

        if token in self.totals:
            self.totals[token] += toAdd
        else:
            self.totals[token] = toAdd

    def track_user_metadata(self, user, metadata):
        if user in self.metadata:
            self.metadata[user].shareSeconds += metadata[user]["shareSeconds"]
            self.metadata[user].shareSecondsInRange += metadata[user][
                "shareSecondsInRange"
            ]
        else:
            self.metadata[user] = DotMap()
            self.metadata[user].shareSeconds = metadata[user]["shareSeconds"]
            self.metadata[user].shareSecondsInRange = metadata[user][
                "shareSecondsInRange"
            ]

    def printState(self):
        # console.log("claims", self.claims.toDict())
        # console.log("tokens", self.tokens.toDict())
        # console.log("cycle", self.cycle)
        table = []
        # console.log("User State", self.users.toDict(), self.totalShareSeconds)
        for user, data in self.claims.items():
            shareSeconds = 0
            shareSecondsInRange = 0
            if user in self.metadata:
                shareSeconds = self.metadata[user].shareSeconds
                shareSecondsInRange = self.metadata[user].shareSecondsInRange
            table.append(
                [
                    user,
                    data["0x3472A5A71965499acd81997a54BBA8D852C6E53d"],
                    shareSeconds,
                    shareSecondsInRange,
                ]
            )
        print("REWARDS LIST")
        print(
            tabulate(
                table, headers=["user", "badger", "shareSeconds", "shareSecondsInRange"]
            )
        )

    def hasToken(self, token):
        if self.tokens[token]:
            return self.tokens[token]
        else:
            return False

    def getTokenRewards(self, user, token):
        if self.claims[user][token]:
            return self.claims[user][token]
        else:
            return 0

    def to_node_entry(self, user, userData, cycle, index):
        """
        Use abi.encode() to encode data into the hex format used as raw node information in the tree
        This is the value that will be hashed to form the rest of the tree  
        """
        nodeEntry = {
            "user": user,
            "tokens": [],
            "cumulativeAmounts": [],
            "cycle": cycle,
            "index": index,
        }
        intAmounts = []
        for tokenAddress, cumulativeAmount in userData.items():
            nodeEntry["tokens"].append(tokenAddress)
            nodeEntry["cumulativeAmounts"].append(str(cumulativeAmount))
            intAmounts.append(int(cumulativeAmount))

        # print(
        #     int(nodeEntry["index"]),
        #     nodeEntry["user"],
        #     int(nodeEntry["cycle"]),
        #     nodeEntry["tokens"],
        #     intAmounts,
        # )

        encoded = encode_hex(
            encode_abi(
                ["uint", "address", "uint", "address[]", "uint[]"],
                (
                    int(nodeEntry["index"]),
                    nodeEntry["user"],
                    int(nodeEntry["cycle"]),
                    nodeEntry["tokens"],
                    intAmounts,
                ),
            )
        )

        # encoder = ClaimEncoder.at(web3.toChecksumAddress("0xf3ff1a5856b1726a8fef921ea57eab2c51466a93"))
        # claim = encoder.encodeClaim(
        #     nodeEntry["tokens"],
        #     nodeEntry["cumulativeAmounts"],
        #     nodeEntry["user"],
        #     nodeEntry["index"],
        #     nodeEntry["cycle"],
        # )[0]

        # console.log("nodeEntry", nodeEntry)
        # print("encoded", encoded)
        # print("claim", claim)

        return (nodeEntry, encoded)

    def to_merkle_format(self):
        """
        - Sort users into alphabetical order
        - Node entry = [cycle, user, index, token[], cumulativeAmount[]]
        """
        cycle = self.cycle
        dict = self.claims.toDict()

        nodeEntries = []
        encodedEntries = []
        entries = []

        index = 0

        for user, userData in self.claims.items():
            (nodeEntry, encoded) = self.to_node_entry(user, userData, cycle, index)
            nodeEntries.append(nodeEntry)
            encodedEntries.append(encoded)
            entries.append({"node": nodeEntry, "encoded": encoded})
            index += 1

        return (nodeEntries, encodedEntries, entries)
