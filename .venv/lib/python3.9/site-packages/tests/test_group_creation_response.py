import json
from datetime import datetime

import pytest
from dateutil.tz import tzutc

from mythx_models.response import (
    GroupCreationResponse,
    GroupState,
    GroupStatistics,
    VulnerabilityStatistics,
)

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-creation-response.json")
OBJ_DATA = GroupCreationResponse.from_json(JSON_DATA)


def assert_response(resp: GroupCreationResponse):
    g = resp.group
    assert g.identifier == "test"
    assert g.name == "test"
    assert g.created_at == datetime(2019, 10, 30, 0, 52, 12, tzinfo=tzutc())
    assert g.created_by == "test"
    assert g.completed_at == datetime(2019, 10, 30, 0, 52, 12, tzinfo=tzutc())
    assert g.progress == 0
    assert g.status == GroupState.OPENED
    assert g.main_source_files == ["test"]
    assert g.analysis_statistics == GroupStatistics(
        total=0, queued=0, running=0, failed=0, finished=0
    )
    assert g.vulnerability_statistics == VulnerabilityStatistics(
        high=0, medium=0, low=0, none=0
    )


def test_from_valid_json():
    assert_response(OBJ_DATA)


# def test_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupCreationResponse.from_json("{}")


def test_from_valid_dict():
    resp = GroupCreationResponse.from_dict(DICT_DATA)
    assert_response(resp)


# def test_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupCreationResponse.from_dict({})


def test_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
