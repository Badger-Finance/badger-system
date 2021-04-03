import json
from copy import deepcopy
from datetime import datetime

import pytest
from dateutil.tz import tzutc

from mythx_models.response import (
    Group,
    GroupListResponse,
    GroupState,
    GroupStatistics,
    VulnerabilityStatistics,
)

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/group-list-response.json")
OBJ_DATA = GroupListResponse.from_json(JSON_DATA)


def assert_response_data(expected, g: Group):
    assert g.identifier == expected["id"]
    assert g.name == expected["name"]
    assert g.created_at == datetime(2019, 11, 4, 13, 38, 23, tzinfo=tzutc())
    assert g.created_by == "test"
    assert g.completed_at == datetime(2019, 11, 4, 13, 38, 23, tzinfo=tzutc())
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
    assert len(OBJ_DATA.groups) == 2
    for i, group in enumerate(OBJ_DATA.groups):
        assert_response_data(DICT_DATA["groups"][i], group)


# def test_from_invalid_json():
#     with pytest.raises(ValidationError):
#         GroupListResponse.from_json("[]")


# def test_from_empty_json():
#     with pytest.raises(ValidationError):
#         GroupListResponse.from_json("{}")


def test_from_valid_dict():
    resp = GroupListResponse.from_dict(DICT_DATA)
    assert len(resp.groups) == 2
    for i, group in enumerate(resp.groups):
        assert_response_data(DICT_DATA["groups"][i], group)


# def test_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         GroupListResponse.from_dict([])


# def test_from_empty_dict():
#     with pytest.raises(ValidationError):
#         GroupListResponse.from_dict({})


def test_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA


def test_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_iteration():
    uuids = ("test1", "test2")
    # XXX: Don't use zip here to make sure __iter__ returns
    for idx, group in enumerate(OBJ_DATA):
        assert uuids[idx] == group.identifier


def test_valid_getitem():
    for idx, group in list(enumerate(OBJ_DATA.groups)):
        assert OBJ_DATA[idx] == group


def test_invalid_getitem_index():
    with pytest.raises(IndexError):
        OBJ_DATA[1337]


def test_oob_getitem_slice():
    OBJ_DATA[1337:9001] == []


def test_valid_delitem():
    group_list = deepcopy(OBJ_DATA)
    del group_list[0]
    assert group_list.groups == OBJ_DATA.groups[1:]
    assert group_list.total == OBJ_DATA.total - 1
    assert len(group_list) == OBJ_DATA.total - 1


def test_invalid_delitem():
    with pytest.raises(IndexError):
        del OBJ_DATA[1337]


def test_valid_setitem():
    group_list = deepcopy(OBJ_DATA)
    group_list[0] = "foo"
    assert group_list.groups[0] == "foo"
    assert group_list[0] == "foo"
    assert len(group_list.groups) == len(OBJ_DATA.groups)


def test_invalid_setitem():
    with pytest.raises(IndexError):
        OBJ_DATA[1337] = "foo"


def test_reversed():
    group_list = deepcopy(OBJ_DATA)
    assert list(reversed(group_list)) == list(reversed(OBJ_DATA.groups))
    assert group_list.total == OBJ_DATA.total


def test_valid_object_contains():
    assert OBJ_DATA.groups[0] in OBJ_DATA


def test_valid_uuid_contains():
    assert OBJ_DATA.groups[0].identifier in OBJ_DATA


def test_contains_error():
    with pytest.raises(ValueError):
        1 in OBJ_DATA


def test_invalid_object_contains():
    group = deepcopy(OBJ_DATA.groups[0])
    group.identifier = "something else"
    assert group not in OBJ_DATA


def test_invalid_uuid_contains():
    assert "foo" not in OBJ_DATA


def test_list_not_equals():
    group_list = deepcopy(OBJ_DATA)
    group_list.total = 0
    assert group_list != OBJ_DATA


def test_nested_not_equals():
    group_list = deepcopy(OBJ_DATA)
    group_list.groups[0].identifier = "foo"
    assert group_list != OBJ_DATA


def test_valid_equals():
    group_list = deepcopy(OBJ_DATA)
    assert group_list == OBJ_DATA
