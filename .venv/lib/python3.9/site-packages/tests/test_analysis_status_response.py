import json
from copy import deepcopy

import pytest

from mythx_models.response import Analysis, AnalysisStatusResponse
from mythx_models.util import serialize_api_timestamp

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/analysis-status-response.json")
OBJ_DATA = AnalysisStatusResponse.from_json(JSON_DATA)


def assert_analysis_data(analysis: Analysis):
    assert DICT_DATA["apiVersion"] == analysis.api_version
    assert DICT_DATA["maruVersion"] == analysis.maru_version
    assert DICT_DATA["mythrilVersion"] == analysis.mythril_version
    assert DICT_DATA["harveyVersion"] == analysis.harvey_version
    assert DICT_DATA["queueTime"] == analysis.queue_time
    assert DICT_DATA["runTime"] == analysis.run_time
    assert DICT_DATA["status"] == analysis.status
    assert DICT_DATA["submittedAt"] == serialize_api_timestamp(analysis.submitted_at)
    assert DICT_DATA["submittedBy"] == analysis.submitted_by
    assert DICT_DATA["uuid"] == analysis.uuid


def test_analysis_list_from_valid_json():
    resp = AnalysisStatusResponse.from_json(JSON_DATA)
    assert_analysis_data(resp.analysis)


# def test_analysis_list_from_empty_json():
#     with pytest.raises(ValidationError):
#         AnalysisStatusResponse.from_json("{}")


def test_analysis_list_from_valid_dict():
    resp = AnalysisStatusResponse.from_dict(DICT_DATA)
    assert_analysis_data(resp.analysis)


# def test_analysis_list_from_empty_dict():
#     with pytest.raises(ValidationError):
#         AnalysisStatusResponse.from_dict({})


def test_analysis_list_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA


def test_analysis_list_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_from_valid_json():
    analysis = Analysis.from_json(json.dumps(DICT_DATA))
    assert_analysis_data(analysis)


def test_analysis_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_analysis_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA


def test_analysis_propagate_error_field():
    analysis = deepcopy(OBJ_DATA.analysis)
    # add optional error field
    analysis.error = "err"
    analysis_dict = analysis.to_dict()
    assert analysis_dict["error"] == "err"


def test_analysis_from_valid_dict():
    analysis = Analysis.from_dict(DICT_DATA)
    assert_analysis_data(analysis)


def test_repr():
    analysis_repr = repr(OBJ_DATA.analysis)
    assert OBJ_DATA.uuid in analysis_repr
    assert OBJ_DATA.status in analysis_repr


def test_unexpected_param():
    data = deepcopy(DICT_DATA)
    data["extra_key"] = "test"
    analysis = Analysis.from_dict(data)
    assert_analysis_data(analysis)
