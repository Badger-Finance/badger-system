from sgqlc.endpoint.http import HTTPEndpoint
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


def fetch_sett_balances(settId,startBlock):
    query = gql("""
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
        """)
    variables = {
        "blockHeight": {
            "number": startBlock
        },
        "vaultID": {
            "id": settId
        }
    }
    results = client.execute(query,variable_values=variables)
    return {
        "balances":results["vaults"][0]["balances"]
    }

def fetch_geyser_events(geyserId,startBlock):
    query = gql("""query($geyserID: Geyser_filter,$blockHeight: Block_height)
    {
      geysers(where: $geyserID,block: $blockHeight) {
          id
          totalStaked
          stakeEvents {
            id
              user,
              amount
              timestamp,
              total
          }
          unstakeEvents {
              id
              user,
              amount
              timestamp,
              total
          }
      }
    }
    """)
    variables = {
      "geyserID": {
        "id":geyserId
      },
      "blockHeight":{
        "number":startBlock
      }
    }
    result = client.execute(query, variable_values=variables)
    return {
        "stakes":result["geyser"][0]]["stakeEvents"]
        "unstakes":result["geyser"][0]["unstakeEvents"]
    }
