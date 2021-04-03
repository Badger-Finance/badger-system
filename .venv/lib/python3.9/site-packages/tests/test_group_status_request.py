import json

import pytest

from mythx_models.request import GroupStatusRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-status-request.json")
OBJ_DATA = GroupStatusRequest.from_json(JSON_DATA)


def assert_request(req: GroupStatusRequest):
    assert req.group_id == "test"
    assert req.method == "GET"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}
    assert req.endpoint == "v1/analysis-groups/test"


# def test_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupStatusRequest.from_json("{}")


def test_from_valid_dict():
    req = GroupStatusRequest.from_dict(json.loads(JSON_DATA))
    assert_request(req)


# def test_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupStatusRequest.from_dict({})


def test_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
