import json

import pytest

from mythx_models.request import DetectedIssuesRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/detected-issues-request.json")
OBJ_DATA = DetectedIssuesRequest.from_json(JSON_DATA)


def test_analysis_issues_request_from_valid_json():
    req = DetectedIssuesRequest.from_json(json.dumps(DICT_DATA))
    assert req.uuid == OBJ_DATA.uuid
    assert req.method == "GET"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}


# def test_analysis_issues_request_from_invalid_json():
#     with pytest.raises(ValidationError):
#         DetectedIssuesRequest.from_json("{}")


def test_analysis_issues_request_from_valid_dict():
    req = DetectedIssuesRequest.from_dict(DICT_DATA)
    assert req.uuid == OBJ_DATA.uuid


# def test_analysis_issues_request_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         DetectedIssuesRequest.from_dict({})


def test_analysis_issues_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_issues_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
