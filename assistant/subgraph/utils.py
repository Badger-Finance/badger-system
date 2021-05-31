from assistant.subgraph.config import subgraph_config
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport


def make_gql_client(name):
    subgraph_url = subgraph_config[name]
    transport = AIOHTTPTransport(url=subgraph_url)
    return Client(transport=transport, fetch_schema_from_transport=True)
