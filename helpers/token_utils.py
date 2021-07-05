from brownie import *
from dotmap import DotMap
from tabulate import tabulate

from helpers.registry import WhaleRegistryAction, registry
from rich.console import Console
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from helpers.utils import val

console = Console()


class BalanceSnapshotter:
    def __init__(self, tokens, accounts):
        self.tokens = tokens
        self.accounts = accounts
        self.snaps = []

    def add_account(self, account):
        # Convert raw addresses into account objects
        if type(account) == str:
            account = accounts.at(account, force=True)
        self.accounts.append(account)

    def snap(self, name="", print=False):
        balances = get_token_balances(self.tokens, self.accounts)
        self.snaps.append({"name": name, "balances": balances})
        if print:
            if name != "":
                console.print(
                    "[green]== Balances: {} ==[/green]".format(
                        name,
                    )
                )
            balances.print()

    def diff_last_two(self):
        num_snaps = len(self.snaps)
        if num_snaps < 2:
            raise Exception("Insufficient snaps have been taken to compare last two")

        before = self.snaps[num_snaps - 2]
        after = self.snaps[num_snaps - 1]

        if before["name"] != "" and after["name"] != "":
            console.print(
                "[green]== Comparing Balances: {} and {} ==[/green]".format(
                    before["name"], after["name"]
                )
            )
        else:
            console.print(
                "[green]== Comparing Balances: Latest two snapshots ==[/green]"
            )
        diff_token_balances(before["balances"], after["balances"], scale=True)


class Balances:
    def __init__(self):
        self.balances = {}

    def set(self, token, account, value):
        if token.address not in self.balances:
            self.balances[token.address] = {}
        self.balances[token.address][account.address] = value

    def get(self, token, account):
        return self.balances[token][account]

    def print(self):
        table = []
        for token, accounts in self.balances.items():
            for account, value in accounts.items():
                table.append(
                    [
                        account,
                        val(value, decimals=token_metadata.get_decimals(token)),
                        token_metadata.get_symbol(token),
                    ]
                )

        print(tabulate(table, headers=["account", "balance", "asset"]))


def diff_token_balances(before, after, scale=True):
    before = before.balances
    after = after.balances
    table = []
    for token, accounts in before.items():
        for account, value in accounts.items():
            if scale:
                amount = (
                    val(
                        after[token][account] - value,
                        decimals=token_metadata.get_decimals(token),
                    ),
                )
            else:
                amount = after[token][account] - value
            table.append([token_metadata.get_symbol(token), account, amount])

    print(tabulate(table, headers=["asset", "account", "balance"]))


def get_token_balances(tokens, accounts):
    balances = Balances()
    for token in tokens:
        for account in accounts:
            balances.set(token, account, token.balanceOf(account))
    return balances


def print_balances(tokens_by_name, account):
    token_contracts = []
    for token_name in tokens_by_name:
        print(token_name, registry.tokens[token_name])
        token_contracts.append(interface.IERC20(registry.tokens[token_name]))
    balances = get_token_balances(token_contracts, [account])

    table = []
    for i, balance in enumerate(balances):
        token_name = tokens_by_name[i]
        token_contract = token_contracts[i]
        table.append([token_name, balance])

    print("\nToken Balances for {}".format(account))
    print(tabulate(table, headers=["asset", "balance"]))


def badger_to_bBadger(badger, amount):
    bBadger = badger.getSett("native.badger")
    ppfs = bBadger.getPricePerFullShare()

    console.print(
        {
            "badger amount": amount,
            "ppfs": ppfs,
            "mult": 10 ** badger.token.decimals(),
            "bBadger amount": amount * 10 ** badger.token.decimals() // ppfs,
        }
    )

    return amount * 10 ** badger.token.decimals() // ppfs


def to_token_scale(asset, unscaled):
    unscaled = float(unscaled)

    address = asset_to_address(asset)
    decimals = token_metadata.get_decimals(address)

    scale_factor = 10 ** decimals

    scaled = unscaled * scale_factor
    print("unscaled", unscaled, decimals, scale_factor, scaled, int(scaled))
    return int(scaled)


class TokenMetadataRegistry:
    def __init__(self):
        self.tokens = {}

    def has(self, address):
        if address in self.tokens.keys():
            return True
        else:
            return False

    def get_decimals(self, address):
        """
        Fetch token decimals from chain on first lookup.
        """
        if not address in self.tokens.keys():
            self.fetch_token_data(address)

        return self.tokens[address]["decimals"]

    def get_symbol(self, address):
        """
        Fetch token symbol from chain on first lookup.
        """
        if not address in self.tokens.keys():
            self.fetch_token_data(address)

        return self.tokens[address]["symbol"]

    def get_name(self, address):
        """
        Fetch token name from chain on first lookup.
        """
        if not address in self.tokens.keys():
            self.fetch_token_data(address)

        return self.tokens[address]["name"]

    def fetch_token_data(self, address):
        token = interface.IERC20(address)
        name = token.name()
        symbol = token.symbol()
        decimals = token.decimals()

        self.tokens[address] = {"name": name, "symbol": symbol, "decimals": decimals}


token_metadata = TokenMetadataRegistry()


def asset_to_address(asset):
    if asset == "badger":
        return registry.tokens.badger
    if asset == "digg":
        return registry.tokens.digg
    if asset == "usdc":
        return registry.tokens.usdc


def to_token(address):
    return interface.IERC20(address)


def distribute_from_whales(recipient, percentage=0.8, assets="All"):

    accounts[0].transfer(recipient, Wei("50 ether"))

    console.print(
        "[green] 🐋 Transferring assets from whales for {} assets... 🐋 [/green]".format(
            len(registry.whales.items())
        )
    )

    # Normal Transfers
    for key, whale_config in registry.whales.items():
        if assets != "All" and key not in assets:
            continue
        # Handle special cases after all standard distributions
        if whale_config.special:
            continue
        if key != "_pytestfixturefunction":
            console.print(" -> {}".format(key))
            distribute_from_whale(whale_config, recipient, percentage=0.8)

    # Special Transfers
    for key, whale_config in registry.whales.items():
        if not whale_config.special:
            continue
        if whale_config.action == WhaleRegistryAction.POPULATE_NEW_SUSHI_LP:
            # Populate LP pair and distribute
            # NOTE: Account should have been distributed both underlying components previously
            sushiswap = SushiswapSystem()
            sushiswap.addMaxLiquidity(
                whale_config.actionParams["token0"],
                whale_config.actionParams["token1"],
                recipient,
            )


def distribute_from_whale(whale_config, recipient, percentage=0.2):
    if whale_config.action == WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT:
        forceEther = ForceEther.deploy({"from": recipient})
        if recipient.balance() < 2 * 10 ** 18:
            distribute_test_ether(recipient, Wei("2 ether"))
        recipient.transfer(forceEther, Wei("2 ether"))
        console.print("Force send Ether to whale..")
        forceEther.forceSend(whale_config.whale, {"from": recipient})

    token = interface.IERC20(whale_config.token)

    console.print("Transfer token {token.address} to recipient")
    token.transfer(
        recipient,
        token.balanceOf(whale_config.whale) * percentage,
        {"from": whale_config.whale},
    )


def distribute_test_ether(recipient, amount):
    """
    On test environments, transfer ETH from default ganache account to specified account
    """
    idx = 0
    while idx < len(accounts):
        if accounts[idx].balance() >= amount:
            break
        idx += 1
    if idx != len(accounts):
        accounts[idx].transfer(recipient, amount)


def getTokenMetadata(address):
    token = interface.IERC20(address)
    name = token.name()
    symbol = token.symbol()
    return (name, symbol, address)


def distribute_meme_nfts(badger, user):
    honeypot_params = DotMap(
        token=badger.token,
        amount=Wei("2500 ether"),
        nftIndicies=[97, 98, 99, 100, 101, 102],
        meme="0xe4605d46Fd0B3f8329d936a8b258D69276cBa264",
        badgerCollection="0x14dC10FA6E4878280F9CA0D9f32dDAEa8C7d4d45",
    )

    memeLtd = interface.IMemeLtd(honeypot_params.meme)
    badgerCollection = accounts.at(honeypot_params.badgerCollection, force=True)

    for index in honeypot_params.nftIndicies:
        console.print("Minting MEME NFT {} for {}...".format(index, user))
        memeLtd.mint(user, index, 1, "0x", {"from": badgerCollection})

    for index in honeypot_params.nftIndicies:
        assert memeLtd.balanceOf(user, index) > 0


def balances(contracts, tokens):
    # Headers
    headers = []
    headers.append("contract")

    for token in tokens:
        headers.append(token.symbol())

    # Balances
    data = []
    for name, c in contracts.items():
        cData = []
        cData.append(name)
        for token in tokens:
            cData.append(token.balanceOf(c) / 1e18)
        data.append(cData)
    print(tabulate(data, headers=headers))
