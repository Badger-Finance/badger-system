from sgqlc.endpoint.http import HTTPEndpoint
from assistant.subgraph.config import subgraph_config
from rich.console import Console

console = Console()

url = subgraph_config["url"]


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
