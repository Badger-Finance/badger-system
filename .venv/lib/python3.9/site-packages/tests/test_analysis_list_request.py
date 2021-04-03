import json
from datetime import datetime

from mythx_models.request import AnalysisListRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/analysis-list-request.json")
OBJ_DATA = AnalysisListRequest.from_json(JSON_DATA)


def assert_analysis_list_request(req):
    assert req.offset == "test"
    assert req.date_from == datetime(2019, 2, 7, 0, 40, 49, 58158)
    assert req.date_to == datetime(2019, 2, 7, 0, 40, 49, 58158)
    assert req.payload == {}
    assert req.method == "GET"
    assert req.parameters == DICT_DATA
    assert req.headers == {}


def test_analysis_list_request_from_valid_json():
    req = AnalysisListRequest.from_json(JSON_DATA)
    assert_analysis_list_request(req)


def test_analysis_list_request_from_empty_json():
    req = AnalysisListRequest.from_json("{}")
    assert req.to_dict() == {
        "offset": None,
        "createdBy": None,
        "groupName": None,
        "dateFrom": None,
        "dateTo": None,
        "groupId": None,
        "mainSource": None,
    }


def test_analysis_list_request_from_valid_dict():
    req = AnalysisListRequest.from_dict(DICT_DATA)
    assert_analysis_list_request(req)


def test_analysis_list_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_list_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
