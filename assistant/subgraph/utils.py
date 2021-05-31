from assistant.subgraph.config import subgraph_config


def make_gql_client(name):
    subgraph_url = subgraph_config[name]
    transport = AIOHTTPTransport(url=tokens_subgraph_url)
    client = Client(transport=tokens_transport, fetch_schema_from_transport=True)
