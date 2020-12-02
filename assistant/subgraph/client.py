from sgqlc.endpoint.http import HTTPEndpoint
from assistant.subgraph.config import subgraph_config

url = subgraph_config["url"]
headers = {"Authorization": "bearer TOKEN"}


def fetch_geyser_events(geyserId, startBlock, endBlock):
    query = "query { geysers {id} }"
    variables = {"geyserId": geyserId}

    endpoint = HTTPEndpoint(url, headers)
    data = endpoint(query, variables)
    print(data)
