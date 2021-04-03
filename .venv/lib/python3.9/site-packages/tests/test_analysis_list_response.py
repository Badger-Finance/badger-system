import json
from copy import deepcopy

import pytest

from mythx_models.response import AnalysisListResponse
from mythx_models.response.analysis import Analysis
from mythx_models.util import serialize_api_timestamp

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/analysis-list-response.json")
OBJ_DATA = AnalysisListResponse.from_json(JSON_DATA)


def assert_analysis_data(expected, analysis: Analysis):
    assert expected["apiVersion"] == analysis.api_version
    assert expected["maruVersion"] == analysis.maru_version
    assert expected["mythrilVersion"] == analysis.mythril_version
    assert expected["harveyVersion"] == analysis.harvey_version
    assert expected["queueTime"] == analysis.queue_time
    assert expected["runTime"] == analysis.run_time
    assert expected["status"] == analysis.status
    assert expected["submittedAt"] == serialize_api_timestamp(analysis.submitted_at)
    assert expected["submittedBy"] == analysis.submitted_by
    assert expected["uuid"] == analysis.uuid
    assert expected["groupName"] == analysis.group_name
    assert expected["groupId"] == analysis.group_id
    assert expected["analysisMode"] == analysis.analysis_mode


def test_analysis_list_from_valid_json():
    assert len(OBJ_DATA.analyses) == 2
    for i, analysis in enumerate(OBJ_DATA.analyses):
        assert_analysis_data(DICT_DATA["analyses"][i], analysis)


# def test_analysis_list_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AnalysisListResponse.from_json("[]")


# def test_analysis_list_from_empty_json():
#     with pytest.raises(ValidationError):
#         AnalysisListResponse.from_json("{}")


def test_analysis_list_from_valid_dict():
    assert len(OBJ_DATA.analyses) == 2
    for i, analysis in enumerate(OBJ_DATA.analyses):
        assert_analysis_data(DICT_DATA["analyses"][i], analysis)


# def test_analysis_list_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AnalysisListResponse.from_dict("[]")


# def test_analysis_list_from_empty_dict():
#     with pytest.raises(ValidationError):
#         AnalysisListResponse.from_dict({})


def test_analysis_list_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA


def test_analysis_list_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_iteration():
    uuids = (
        "0680a1e2-b908-4c9a-a15b-636ef9b61486",
        "0680a1e2-b908-4c9a-a15b-636ef9b61487",
    )
    # XXX: Don't use zip here to make sure __iter__ returns
    for idx, analysis in enumerate(OBJ_DATA):
        assert uuids[idx] == analysis.uuid


def test_valid_getitem():
    for idx, analysis in list(enumerate(OBJ_DATA.analyses)):
        assert OBJ_DATA[idx] == analysis


def test_invalid_getitem_index():
    with pytest.raises(IndexError):
        OBJ_DATA[1337]


def test_oob_getitem_slice():
    assert OBJ_DATA[1337:9001] == []


def test_valid_delitem():
    analysis_list = deepcopy(OBJ_DATA)
    del analysis_list[0]
    assert analysis_list.analyses == OBJ_DATA[1:]
    assert analysis_list.total == OBJ_DATA.total - 1
    assert len(analysis_list) == OBJ_DATA.total - 1


def test_invalid_delitem():
    with pytest.raises(IndexError):
        del OBJ_DATA[1337]


def test_valid_setitem():
    analysis_list = deepcopy(OBJ_DATA)
    analysis_list[0] = "foo"
    assert analysis_list.analyses[0] == "foo"
    assert analysis_list[0] == "foo"
    assert len(analysis_list.analyses) == len(OBJ_DATA.analyses)


def test_invalid_setitem():
    with pytest.raises(IndexError):
        OBJ_DATA[1337] = "foo"


def test_reversed():
    analysis_list = deepcopy(OBJ_DATA)
    assert list(reversed(analysis_list)) == list(reversed(OBJ_DATA.analyses))
    assert analysis_list.total == OBJ_DATA.total


def test_valid_object_contains():
    assert OBJ_DATA.analyses[0] in OBJ_DATA


def test_valid_uuid_contains():
    assert OBJ_DATA.analyses[0].uuid in OBJ_DATA


def test_contains_error():
    with pytest.raises(ValueError):
        1 in OBJ_DATA


def test_invalid_object_contains():
    analysis = deepcopy(OBJ_DATA.analyses[0])
    analysis.uuid = "something else"
    assert analysis not in OBJ_DATA


def test_invalid_uuid_contains():
    assert "foo" not in OBJ_DATA


def test_list_not_equals():
    analysis_list = deepcopy(OBJ_DATA)
    analysis_list.total = 0
    assert analysis_list != OBJ_DATA


def test_nested_analysis_not_equals():
    analysis_list = deepcopy(OBJ_DATA)
    analysis_list.analyses[0].uuid = "foo"
    assert analysis_list != OBJ_DATA


def test_valid_equals():
    analysis_list = deepcopy(OBJ_DATA)
    assert analysis_list == OBJ_DATA
