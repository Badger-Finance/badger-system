from brownie import *
from dotmap import DotMap
from rich.console import Console
from eth_utils.hexadecimal import encode_hex
from tabulate import tabulate

console = Console()


class RewardsList:
    def __init__(self, cycle, badgerTree) -> None:
        self.claims = DotMap()
        self.tokens = DotMap()
        self.totals = DotMap()
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
        nodeEntry = {
            "user": user,
            "tokens": [],
            "cumulativeAmounts": [],
            "cycle": cycle,
            "index": index,
        }
        for tokenAddress, cumulativeAmount in userData.items():
            nodeEntry["tokens"].append(tokenAddress)
            nodeEntry["cumulativeAmounts"].append(str(cumulativeAmount))

        # encoded = encode_hex(
        #     encode_abi_packed(
        #         ["uint", "address", "uint", "address[]", "uint[]"],
        #         (
        #             nodeEntry["index"],
        #             nodeEntry["user"],
        #             nodeEntry["cycle"],
        #             nodeEntry["tokens"],
        #             nodeEntry["cumulativeAmounts"],
        #         ),
        #     )
        # )

        encoder = ClaimEncoder.at("0x19be80e976cb397ae584d350153914ced7c1b1d2")

        claim = encoder.encodeClaim(
            nodeEntry["tokens"],
            nodeEntry["cumulativeAmounts"],
            nodeEntry["index"],
            nodeEntry["cycle"],
            nodeEntry["user"],
        )[0]

        # print ('claim', claim)

        encoded = encode_hex(claim)

        # console.log("nodeEntry", nodeEntry)
        # console.log("encoded", encoded)
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
