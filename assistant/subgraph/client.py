from assistant.subgraph.config import subgraph_config
from rich.console import Console

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

console = Console()

url = subgraph_config["url"]
transport = AIOHTTPTransport(url=url)
client = Client(transport=transport, fetch_schema_from_transport=True)


def fetch_all_geyser_events(geyserId):
    print("fetch_geyser_events", geyserId)
    # Get all geysers
    query = """
    {
    geysers {
        id
        totalStaked
        stakeEvents(orderBy: blockNumber) {
        id, geyser {
            id
        }, user, amount, total, timestamp, blockNumber, data
            }
        unstakeEvents(orderBy: blockNumber) {
        id, geyser {
            id
        }, user, amount, total, timestamp, blockNumber, data
            }
    }
    }
    """

    variables = {"geyserId": geyserId}
    endpoint = HTTPEndpoint(url, headers)
    result = endpoint(query)

    unstakes = []
    stakes = []
    totalStaked = 0

    # Find this geyser
    for entry in result["data"]["geysers"]:
        if entry["id"] == geyserId:
            stakes = entry["stakeEvents"]
            unstakes = entry["unstakeEvents"]
            totalStaked = entry["totalStaked"]

    # console.log(result['data'])
    return {
        "id": geyserId,
        "unstakes": unstakes,
        "stakes": stakes,
        "totalStaked": totalStaked,
    }


def fetch_sett_balances(settId, startBlock):
    console.print(
        "[bold green] Fetching sett balances {}[/bold green]".format(settId)
    )
    query = gql(
        """
        query balances_and_events($vaultID: Vault_filter, $blockHeight: Block_height) {
            vaults(block: $blockHeight, where: $vaultID) {
                balances(orderBy: netDeposits, orderDirection: desc) {
                    id
                    account {
                        id
                    }
                    shareBalanceRaw
                  }
                }
            }
        """
    )
    variables = {"blockHeight": {"number": startBlock}, "vaultID": {"id": settId}}
    results = client.execute(query, variable_values=variables)
    balances = {}
    for result in results["vaults"][0]["balances"]:
        account = result["id"].split("-")[0]
        balances[account] = int(result["shareBalanceRaw"])
    return balances


def fetch_geyser_events(geyserId, startBlock):
    console.print(
        "[bold green] Fetching Geyser Events {}[/bold green]".format(geyserId)
    )

    query = gql(
        """query($geyserID: Geyser_filter,$blockHeight: Block_height)
    {
      geysers(where: $geyserID,block: $blockHeight) {
          id
          totalStaked
          stakeEvents(first:1000) {
            id
              user,
              amount
              timestamp,
              total
          }
          unstakeEvents(first:1000) {
              id
              user,
              amount
              timestamp,
              total
          }
      }
    }
    """
    )
    variables = {"geyserID": {"id": geyserId}, "blockHeight": {"number": startBlock}}
    result = client.execute(query, variable_values=variables)
    return {
        "stakes": result["geysers"][0]["stakeEvents"],
        "unstakes": result["geysers"][0]["unstakeEvents"],
        "totalStaked": result["geysers"][0]["totalStaked"],
    }


def fetch_sett_transfers(settID, startBlock, endBlock):
    endBlock = endBlock - 1
    console.print(
        "[bold green] Fetching Sett Deposits/Withdrawals {}[/bold green]".format(settID)
    )
    query = gql(
        """
        query sett_transfers($vaultID: Vault_filter, $blockHeight: Block_height) {
            vaults(block: $blockHeight, where: $vaultID) {
                pricePerFullShare
                deposits(first:1000) {
                    account {
                     id
                    }
                    amount
                    transaction {
                        timestamp
                        blockNumber
                    }
                }
                withdrawals(first:1000) {
                    account {
                     id
                    }
                    amount
                    transaction {
                        timestamp
                        blockNumber
                    }
                }
            }
        }
    """
    )
    variables = {"vaultID": {"id": settID}, "blockHeight": {"number": endBlock}}

    results = client.execute(query, variable_values=variables)
    pricePerFullShare = results["vaults"][0]["pricePerFullShare"]

    def filter_by_startBlock(transfer):
            return int(transfer["transaction"]["blockNumber"]) > startBlock

    def convert_amount(transfer):
        transfer["amount"] = int(transfer["amount"]) / float(pricePerFullShare)
        return transfer

    def negate_withdrawals(withdrawal):
        withdrawal["amount"] = -withdrawal["amount"]
        return withdrawal



    deposits = map(convert_amount, results["vaults"][0]["deposits"])
    withdrawals = map(
        negate_withdrawals,
        map(convert_amount, results["vaults"][0]["withdrawals"]),
    )

    deposits = filter(filter_by_startBlock, list(deposits))
    withdrawals = filter(filter_by_startBlock, list(withdrawals))
    return sorted(
        [*list(deposits), *list(withdrawals)],
        key=lambda t: t["transaction"]["timestamp"],
    )
