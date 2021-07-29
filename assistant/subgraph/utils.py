from assistant.subgraph.config import subgraph_ids, subgraph_urls
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from config.env_config import env_config


def subgraph_url(name):
    if name in subgraph_ids:
        return "https://gateway.thegraph.com/api/{}/subgraphs/id/{}".format(
            env_config.graph_api_key, subgraph_ids[name]
        )
    elif name in subgraph_urls:
        return subgraph_urls[name]


def make_gql_client(name):
    url = subgraph_url(name)
    print(url)
    transport = AIOHTTPTransport(url=url)
    return Client(transport=transport, fetch_schema_from_transport=True)
