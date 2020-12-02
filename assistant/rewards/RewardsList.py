class RewardsList:
    def __init__(self, cycle) -> None:
        self.claims = DotMap()
        self.tokens = DotMap()
        self.totals = DotMap()
        self.cycle = cycle

    def increase_user_rewards(self, user, token, toAdd):
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

    def printState(self):
        console.log("claims", self.claims.toDict())
        console.log("tokens", self.tokens.toDict())
        console.log("cycle", self.cycle)

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
            nodeEntry["cumulativeAmounts"].append(cumulativeAmount)

        encoded = encode_hex(
            encode_abi_packed(
                ["uint", "address", "uint", "address[]", "uint[]"],
                (
                    nodeEntry["index"],
                    nodeEntry["user"],
                    nodeEntry["cycle"],
                    nodeEntry["tokens"],
                    nodeEntry["cumulativeAmounts"],
                ),
            )
        )

        console.log("nodeEntry", nodeEntry)
        console.log("encoded", encoded)
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