import json

import pytest

from mythx_models.request import GroupOperationRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-operation-request.json")
OBJ_DATA = GroupOperationRequest.from_json(JSON_DATA)


def assert_request(req):
    assert req.group_id == "test"
    assert req.method == "POST"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {"type": "test"}
    assert req.endpoint == "v1/analysis-groups/test"


def test_from_valid_json():
    req = GroupOperationRequest.from_json(json.dumps(DICT_DATA))
    assert_request(req)


# def test_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupOperationRequest.from_json("{}")


def test_from_valid_dict():
    req = GroupOperationRequest.from_dict(DICT_DATA)
    assert_request(req)


# def test_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupOperationRequest.from_dict({})


def test_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
