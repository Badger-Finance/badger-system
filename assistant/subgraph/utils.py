from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from assistant.subgraph.config import subgraph_config


def make_client(name):
    subgraph_url = subgraph_config[name]
    subgraph_transport = AIOHTTPTransport(url=subgraph_url)
    return Client(transport=subgraph_transport, fetch_schema_from_transport=True)
