import json
from copy import deepcopy
from typing import Dict

import pytest

from mythx_models.response import (
    DetectedIssuesResponse,
    Issue,
    IssueReport,
    Severity,
    SourceFormat,
    SourceLocation,
    SourceType,
)

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/detected-issues-response.json")
OBJ_DATA = DetectedIssuesResponse.from_json(JSON_DATA)


def assert_detected_issues(resp):
    assert len(resp.issue_reports) == 1
    report = resp.issue_reports[0]
    assert type(report) == IssueReport
    issue = report.issues[0]
    assert_issue(issue, DICT_DATA[0]["issues"][0])


def assert_issue(issue: Issue, data: Dict, skip_decoded: bool = False):
    assert issue.swc_id == data["swcID"]
    assert issue.swc_title == data["swcTitle"]
    assert issue.description_short == data["description"]["head"]
    assert issue.description_long == data["description"]["tail"]
    assert issue.severity == Severity(data["severity"])
    if not skip_decoded:
        assert issue.decoded_locations[0].to_dict() == data["decodedLocations"][0]
    assert len(issue.locations) == 1
    location = issue.locations[0]
    assert location.source_map.to_sourcemap() == data["locations"][0]["sourceMap"]
    assert location.source_format == SourceFormat(data["locations"][0]["sourceFormat"])
    assert location.source_type == SourceType(data["locations"][0]["sourceType"])
    assert location.source_list == data["locations"][0]["sourceList"]


def test_detected_issues_from_valid_json():
    resp = DetectedIssuesResponse.from_json(JSON_DATA)
    assert_detected_issues(resp)


def test_detected_issues_from_empty_json():
    resp = DetectedIssuesResponse.from_json("[]")
    assert resp.issue_reports == []


def test_detected_issues_from_dict():
    resp = DetectedIssuesResponse.from_dict(DICT_DATA)
    assert_detected_issues(resp)


def test_detected_issues_from_list():
    resp = DetectedIssuesResponse.from_dict([DICT_DATA[0]])
    assert_detected_issues(resp)


# def test_detected_issues_from_invalid_type():
#     with pytest.raises(ValidationError):
#         DetectedIssuesResponse.from_dict("foo")


def test_detected_issues_from_empty_list():
    resp = DetectedIssuesResponse.from_dict([])
    assert resp.issue_reports == []


# def test_detected_issues_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         DetectedIssuesResponse.from_dict({})


def test_detected_issues_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_valid_swc_id_contains():
    assert DICT_DATA[0]["issues"][0]["swcID"] in OBJ_DATA


def test_valid_swc_id_not_contains():
    assert "SWC-104" not in OBJ_DATA


def test_invalid_key_contains():
    with pytest.raises(ValueError):
        1337 in OBJ_DATA


def test_response_length():
    resp = deepcopy(OBJ_DATA)
    total_report_issues = len(resp)
    assert len(resp) == total_report_issues
    resp.issue_reports.append(
        IssueReport(
            issues=["foo", "bar"],
            source_type=SourceType.RAW_BYTECODE,
            source_format=SourceFormat.EVM_BYZANTIUM_BYTECODE,
            source_list="foo.sol",
            meta_data={},
        )
    )
    assert len(resp) == total_report_issues + 2


def test_issue_iterator():
    for i, report in enumerate(OBJ_DATA.issue_reports):
        assert OBJ_DATA.issue_reports[i] == report


def test_report_iterator():
    for i, issue in enumerate(OBJ_DATA):
        assert issue == OBJ_DATA.issue_reports[0][i]


def test_issue_valid_getitem():
    assert OBJ_DATA.issue_reports[0] == OBJ_DATA[0]


def test_report_getitem():
    for i, issue in enumerate(OBJ_DATA):
        assert issue == OBJ_DATA.issue_reports[0][i]


def test_invalid_getitem():
    with pytest.raises(IndexError):
        test = OBJ_DATA[1337]


def test_valid_setitem():
    resp = deepcopy(OBJ_DATA)
    resp[0] = "foo"
    assert resp.issue_reports[0] == "foo"


def test_report_valid_setitem():
    resp = deepcopy(OBJ_DATA)
    resp.issue_reports[0][0] = "foo"
    assert resp.issue_reports[0][0] == "foo"


def test_invalid_setitem():
    with pytest.raises(TypeError):
        # string key on list access
        OBJ_DATA.issue_reports["foo"] = "bar"


def test_report_invalid_setitem():
    with pytest.raises(TypeError):
        # string key on list access
        OBJ_DATA.issue_reports[0]["foo"] = "bar"


def test_valid_delete():
    resp = deepcopy(OBJ_DATA)
    del resp[0]
    assert resp.issue_reports == []


def test_valid_report_delete():
    resp = deepcopy(OBJ_DATA)
    del resp[0][0]
    assert resp.issue_reports[0].issues == []


def test_invalid_delete():
    with pytest.raises(IndexError):
        del OBJ_DATA[1337]


def test_invalid_report_delete():
    with pytest.raises(IndexError):
        del OBJ_DATA[0][100]


def test_issue_from_valid_json():
    issue = Issue.from_json(json.dumps(DICT_DATA[0]["issues"][0]))
    assert_issue(issue, DICT_DATA[0]["issues"][0])


def test_issue_from_dict():
    issue = Issue.from_dict(DICT_DATA[0]["issues"][0])
    assert_issue(issue, DICT_DATA[0]["issues"][0])


def test_issue_to_json():
    assert (
        json.loads(OBJ_DATA.issue_reports[0][0].to_json()) == DICT_DATA[0]["issues"][0]
    )


def test_issue_to_dict():
    assert OBJ_DATA.issue_reports[0][0].to_dict() == DICT_DATA[0]["issues"][0]


def test_source_location_from_dict():
    loc2 = DICT_DATA[0]["issues"][0]["locations"][0]
    sl = SourceLocation.from_dict(loc2)
    assert sl.source_format == loc2["sourceFormat"]
    assert sl.source_list == loc2["sourceList"]
    assert sl.source_map.to_sourcemap() == loc2["sourceMap"]
    assert sl.source_type == loc2["sourceType"]


def test_decoded_locations_removed():
    issue_data = deepcopy(DICT_DATA[0]["issues"][0])
    del issue_data["decodedLocations"]
    issue = Issue.from_dict(issue_data)
    assert_issue(issue, DICT_DATA[0]["issues"][0], skip_decoded=True)
    assert "decodedLocations" not in issue.to_dict()


def test_decoded_locations_empty_removed():
    issue_data = deepcopy(DICT_DATA[0]["issues"][0])
    issue_data["decodedLocations"] = []
    issue = Issue.from_dict(issue_data)
    assert_issue(issue, DICT_DATA[0]["issues"][0], skip_decoded=True)
    assert "decodedLocations" not in issue.to_dict()


def test_decoded_locations_only_removed():
    issue_data = deepcopy(DICT_DATA[0]["issues"][0])
    issue_data["decodedLocations"] = [[]]
    issue = Issue.from_dict(issue_data)
    assert_issue(issue, DICT_DATA[0]["issues"][0], skip_decoded=True)
    assert issue.to_dict().get("decodedLocations") == [[]]


def test_decoded_locations_empty_skip():
    issue_data = deepcopy(DICT_DATA[0]["issues"][0])
    issue_data["decodedLocations"].append([])
    issue = Issue.from_dict(issue_data)
    assert_issue(issue, DICT_DATA[0]["issues"][0], skip_decoded=True)
    assert "decodedLocations" in issue.to_dict()


def test_decoded_locations_none_skip():
    issue_data = deepcopy(DICT_DATA[0]["issues"][0])
    issue_data["decodedLocations"] = None
    issue = Issue.from_dict(issue_data)
    assert_issue(issue, DICT_DATA[0]["issues"][0], skip_decoded=True)
    print(issue.to_dict())
    assert "decodedLocations" not in issue.to_dict()
