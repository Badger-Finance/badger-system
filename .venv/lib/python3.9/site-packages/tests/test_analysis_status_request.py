import json

import pytest

from mythx_models.request import AnalysisStatusRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/analysis-status-request.json")
OBJ_DATA = AnalysisStatusRequest.from_json(JSON_DATA)


def assert_status_request(req: AnalysisStatusRequest):
    assert req.uuid == OBJ_DATA.uuid
    assert req.method == "GET"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}


def test_analysis_status_request_from_valid_json():
    req = AnalysisStatusRequest.from_json(JSON_DATA)
    assert_status_request(req)


# def test_analysis_status_request_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AnalysisStatusRequest.from_json("{}")


def test_analysis_status_request_from_valid_dict():
    req = AnalysisStatusRequest.from_dict(DICT_DATA)
    assert_status_request(req)


# def test_analysis_status_request_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AnalysisStatusRequest.from_dict({})


def test_analysis_status_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_status_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
