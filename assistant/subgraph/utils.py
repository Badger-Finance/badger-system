from assistant.subgraph.config import subgraph_ids
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from config.env_config import env_config


def subgraph_url(name):
    subgraphId = subgraph_ids[name]
    return "https://gateway.thegraph.com/api/{}/subgraphs/id/{}".format(
        env_config.graph_api_key, subgraphId
    )


def make_gql_client(name):
    transport = AIOHTTPTransport(url=subgraph_url(name))
    return Client(transport=transport, fetch_schema_from_transport=True)
