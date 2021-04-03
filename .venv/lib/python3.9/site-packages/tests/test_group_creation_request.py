import json

import pytest

from mythx_models.request import GroupCreationRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-creation-request.json")
OBJ_DATA = GroupCreationRequest.from_json(JSON_DATA)


def assert_request(req):
    assert req.group_name == "test"
    assert req.method == "POST"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {"groupName": "test"}
    assert req.endpoint == "v1/analysis-groups"


def test_from_valid_json():
    req = GroupCreationRequest.from_json(json.dumps(DICT_DATA))
    assert_request(req)


# def test_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupCreationRequest.from_json("{}")


def test_from_valid_dict():
    req = GroupCreationRequest.from_dict(DICT_DATA)
    assert_request(req)


# def test_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupCreationRequest.from_dict({})


def test_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
