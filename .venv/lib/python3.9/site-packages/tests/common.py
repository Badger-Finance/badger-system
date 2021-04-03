import json
from pathlib import Path


def get_test_case(path: str, obj=None):
    with open(str(Path(__file__).parent / path)) as f:
        dict_data = json.load(f)

    if obj is None:
        return dict_data
    return obj.from_dict(dict_data)


def generate_request_dict(req):
    return {
        "method": req.method,
        "payload": req.payload,
        "params": req.parameters,
        "headers": req.headers,
        "url": "https://test.com/" + req.endpoint,
    }
