import json
from datetime import datetime

import pytest

from mythx_models.request import GroupListRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-list-request.json")
OBJ_DATA = GroupListRequest.from_json(JSON_DATA)


def assert_request(req: GroupListRequest):
    assert req.offset == "test"
    assert req.created_by == "test"
    assert req.group_name == "test"
    assert req.date_from == datetime(2019, 2, 7, 0, 40, 49, 58158)
    assert req.date_to == datetime(2019, 2, 7, 0, 40, 49, 58158)
    assert req.payload == {}
    assert req.method == "GET"
    assert req.parameters == DICT_DATA
    assert req.headers == {}
    assert req.endpoint == "v1/analysis-groups"


def test_analysis_list_request_from_valid_json():
    req = GroupListRequest.from_json(json.dumps(DICT_DATA))
    assert_request(req)


# def test_analysis_list_request_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupListRequest.from_json("{}")


def test_analysis_list_request_from_valid_dict():
    req = GroupListRequest.from_dict(DICT_DATA)
    assert_request(req)


# def test_analysis_list_request_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupListRequest.from_dict({})


def test_analysis_list_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_list_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
