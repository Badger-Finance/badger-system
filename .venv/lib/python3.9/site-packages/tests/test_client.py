import json
from copy import copy
from datetime import datetime

import jwt
import mythx_models.response as respmodels
import pytest
from dateutil.tz import tzutc
from mythx_models.exceptions import ValidationError
from mythx_models.response.analysis import AnalysisStatus
from mythx_models.util import serialize_api_timestamp

from pythx.api import APIHandler, Client
from pythx.middleware.analysiscache import AnalysisCacheMiddleware
from pythx.middleware.toolname import ClientToolNameMiddleware

from .common import get_test_case


class MockAPIHandler(APIHandler):
    def __init__(self, resp):
        super().__init__()
        self.resp = resp

    def send_request(self, *args, **kwargs):
        return json.dumps(self.resp.pop(0))


def get_client(resp_data, logged_in=True, access_expired=False, refresh_expired=False):
    client = Client(
        username="0xdeadbeef", password="supersecure", handler=MockAPIHandler(resp_data)
    )
    if logged_in:
        # simulate that we're already logged in with tokens
        client.api_key = jwt.encode(
            {
                "exp": datetime(1994, 7, 29, tzinfo=tzutc())
                if access_expired
                else datetime(9999, 1, 1, tzinfo=tzutc())
            },
            "secret",
        )
        client.refresh_token = jwt.encode(
            {
                "exp": datetime(1994, 7, 29, tzinfo=tzutc())
                if refresh_expired
                else datetime(9999, 1, 1, tzinfo=tzutc())
            },
            "secret",
        )

    return client


def assert_middlewares(client: Client):
    type_list = [type(x) for x in client.handler.middlewares]
    assert ClientToolNameMiddleware in type_list
    assert AnalysisCacheMiddleware in type_list
    assert len(type_list) == 2


def test_login():
    test_dict = get_test_case("testdata/auth-login-response.json")
    client = get_client([test_dict], logged_in=False)

    assert client.api_key is None
    assert client.refresh_token is None

    resp = client.login()

    assert type(resp) == respmodels.AuthLoginResponse
    assert resp.api_key == test_dict["jwtTokens"]["access"]
    assert resp.refresh_token == test_dict["jwtTokens"]["refresh"]

    assert client.api_key == test_dict["jwtTokens"]["access"]
    assert client.refresh_token == test_dict["jwtTokens"]["refresh"]


def test_logout():
    test_dict = get_test_case("testdata/auth-logout-response.json")
    client = get_client([test_dict])
    resp = client.logout()

    assert type(resp) == respmodels.AuthLogoutResponse
    assert client.api_key is None
    assert client.refresh_token is None


def test_refresh():
    test_dict = get_test_case("testdata/auth-refresh-response.json")
    client = get_client([test_dict])
    resp = client.refresh()

    assert type(resp) == respmodels.AuthRefreshResponse
    assert resp.access_token == test_dict["jwtTokens"]["access"]
    assert resp.refresh_token == test_dict["jwtTokens"]["refresh"]
    assert resp.to_dict() == test_dict

    assert client.api_key == test_dict["jwtTokens"]["access"]
    assert client.refresh_token == test_dict["jwtTokens"]["refresh"]


def test_group_list():
    test_dict = get_test_case("testdata/group-list-response.json")
    client = get_client([test_dict])
    resp = client.group_list()

    assert type(resp) == respmodels.GroupListResponse
    assert resp.total == len(test_dict["groups"])
    assert resp.to_dict() == test_dict


def test_group_status():
    test_dict = get_test_case("testdata/group-status-response.json")
    client = get_client([test_dict])
    resp = client.group_status(group_id="test")

    assert type(resp) == respmodels.GroupStatusResponse
    assert resp.to_dict() == test_dict


def test_group_open():
    test_dict = get_test_case("testdata/group-operation-response.json")
    client = get_client([test_dict])
    resp = client.create_group(group_name="test")

    assert type(resp) == respmodels.GroupCreationResponse
    assert resp.to_dict() == test_dict


def test_group_seal():
    test_dict = get_test_case("testdata/group-operation-response.json")
    client = get_client([test_dict])
    resp = client.seal_group(group_id="test")

    assert type(resp) == respmodels.GroupOperationResponse
    assert resp.to_dict() == test_dict


def test_request_by_uuid():
    test_dict = get_test_case("testdata/analysis-input-response.json")
    client = get_client([test_dict])
    resp = client.request_by_uuid(uuid="test")

    assert type(resp) == respmodels.AnalysisInputResponse
    assert resp.to_dict() == test_dict


def test_analysis_list():
    test_dict = get_test_case("testdata/analysis-list-response.json")
    client = get_client([test_dict])
    resp = client.analysis_list(
        date_from=datetime(2018, 1, 1), date_to=datetime(2019, 1, 1)
    )

    assert type(resp) == respmodels.AnalysisListResponse
    assert resp.total == len(test_dict["analyses"])
    assert resp.to_dict() == test_dict


def test_auto_login():
    login_dict = get_test_case("testdata/auth-login-response.json")
    list_dict = get_test_case("testdata/analysis-list-response.json")
    client = get_client([login_dict, list_dict], logged_in=False)
    resp = client.analysis_list(
        date_from=datetime(2018, 1, 1), date_to=datetime(2019, 1, 1)
    )
    assert type(resp) == respmodels.AnalysisListResponse
    assert resp.total == len(list_dict["analyses"])
    assert resp.to_dict() == list_dict


def test_expired_auth_and_refresh_token():
    login_dict = get_test_case("testdata/auth-login-response.json")
    list_dict = get_test_case("testdata/analysis-list-response.json")
    client = get_client(
        [login_dict, list_dict],
        logged_in=True,
        access_expired=True,
        refresh_expired=True,
    )
    resp = client.analysis_list(
        date_from=datetime(2018, 1, 1), date_to=datetime(2019, 1, 1)
    )
    assert type(resp) == respmodels.AnalysisListResponse
    assert resp.total == len(list_dict["analyses"])
    assert resp.to_dict() == list_dict


def test_expired_api_key():
    refresh_dict = get_test_case("testdata/auth-refresh-response.json")
    list_dict = get_test_case("testdata/analysis-list-response.json")
    client = get_client([refresh_dict, list_dict], logged_in=True, access_expired=True)
    resp = client.analysis_list(
        date_from=datetime(2018, 1, 1), date_to=datetime(2019, 1, 1)
    )
    assert type(resp) == respmodels.AnalysisListResponse
    assert resp.total == len(list_dict["analyses"])
    assert resp.to_dict() == list_dict


def assert_analysis(expected, analysis):
    assert analysis.uuid == expected["uuid"]
    assert analysis.api_version == expected["apiVersion"]
    assert analysis.mythril_version == expected["mythrilVersion"]
    assert analysis.maru_version == expected["maruVersion"]
    assert analysis.run_time == expected["runTime"]
    assert analysis.queue_time == expected["queueTime"]
    assert analysis.status == AnalysisStatus(expected["status"])
    assert serialize_api_timestamp(analysis.submitted_at) == expected["submittedAt"]
    assert analysis.submitted_by == expected["submittedBy"]


def test_analyze_bytecode():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    client = get_client([test_dict])
    resp = client.analyze(bytecode="0xf00")

    assert type(resp) == respmodels.AnalysisSubmissionResponse
    assert_analysis(test_dict, resp.analysis)


def test_analyze_source_code():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    client = get_client([test_dict])
    resp = client.analyze(sources={"foo.sol": {"source": "bar"}})

    assert type(resp) == respmodels.AnalysisSubmissionResponse
    assert_analysis(test_dict, resp.analysis)


def test_analyze_source_and_bytecode():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    client = get_client([test_dict])
    resp = client.analyze(sources={"foo.sol": {"source": "bar"}}, bytecode="0xf00")
    assert type(resp) == respmodels.AnalysisSubmissionResponse
    assert_analysis(test_dict, resp.analysis)


# def test_analyze_missing_data():
#     test_dict = get_test_case("testdata/analysis-submission-response.json")
#     client = get_client([test_dict])
#     with pytest.raises(ValidationError):
#         client.analyze()


# def test_analyze_invalid_mode():
#     test_dict = get_test_case("testdata/analysis-submission-response.json")
#     client = get_client([test_dict])
#     with pytest.raises(ValidationError):
#         client.analyze(bytecode="0xf00", analysis_mode="invalid")


def test_status():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    client = get_client([test_dict])
    resp = client.status(uuid=test_dict["uuid"])

    assert type(resp) == respmodels.AnalysisStatusResponse
    assert_analysis(test_dict, resp.analysis)


def test_running_analysis_not_ready():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    client = get_client([test_dict])
    resp = client.analysis_ready(uuid=test_dict["uuid"])
    assert resp is False


def test_queued_analysis_not_ready():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    data = copy(test_dict)
    data["status"] = "Queued"
    client = get_client([data])
    resp = client.analysis_ready(uuid=test_dict["uuid"])
    assert resp is False


def test_finished_analysis_ready():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    data = copy(test_dict)
    data["status"] = "Finished"
    client = get_client([data])
    resp = client.analysis_ready(uuid=test_dict["uuid"])
    assert resp is True


def test_error_analysis_ready():
    test_dict = get_test_case("testdata/analysis-submission-response.json")
    data = copy(test_dict)
    data["status"] = "Error"
    client = get_client([data])
    resp = client.analysis_ready(uuid=test_dict["uuid"])
    assert resp is True


def test_report():
    test_dict = get_test_case("testdata/detected-issues-response.json")
    expected_report = test_dict[0]
    expected_issue = expected_report["issues"][0]
    expected_location = expected_issue["locations"][0]
    client = get_client([test_dict])
    resp = client.report(uuid="test")

    assert type(resp) == respmodels.DetectedIssuesResponse
    assert resp.issue_reports[0].source_type == expected_report["sourceType"]
    assert resp.issue_reports[0].source_format == expected_report["sourceFormat"]
    assert resp.issue_reports[0].source_list == expected_report["sourceList"]
    assert resp.issue_reports[0].meta_data == {}
    assert len(resp) == 1

    issue = resp.issue_reports[0].issues[0]
    assert issue.swc_id == expected_issue["swcID"]
    assert issue.swc_title == expected_issue["swcTitle"]
    assert issue.description_short == expected_issue["description"]["head"]
    assert issue.description_long == expected_issue["description"]["tail"]
    assert issue.severity == expected_issue["severity"]
    assert issue.extra_data == {}
    assert len(issue.locations) == 1

    location = issue.locations[0]
    assert location.source_map.to_sourcemap() == expected_location["sourceMap"]
    assert location.source_type == expected_location["sourceType"]
    assert location.source_format == expected_location["sourceFormat"]
    assert location.source_list == expected_location["sourceList"]


def test_openapi():
    client = get_client(["OpenAPI stuff"])
    resp = client.openapi()
    assert type(resp) == respmodels.OASResponse
    # we have to wrap this into quotes here because
    # of the test handler - content stays the same.
    assert resp.data == '"{}"'.format("OpenAPI stuff")


def test_version():
    test_dict = get_test_case("testdata/version-response.json")
    client = get_client([test_dict])
    resp = client.version()
    assert type(resp) == respmodels.VersionResponse
    assert resp.api_version == test_dict["api"]
    assert resp.maru_version == test_dict["maru"]
    assert resp.mythril_version == test_dict["mythril"]
    assert resp.harvey_version == test_dict["harvey"]
    assert resp.hashed_version == test_dict["hash"]


def test_jwt_expiration():
    test_dict = get_test_case("testdata/auth-login-response.json")
    assert Client._get_jwt_expiration_ts(test_dict["jwtTokens"]["access"]) == datetime(
        2019, 2, 24, 16, 31, 19, 28000
    )
    assert Client._get_jwt_expiration_ts(test_dict["jwtTokens"]["refresh"]) == datetime(
        2019, 3, 24, 16, 21, 19, 28000
    )


def test_context_handler():
    test_dict = get_test_case("testdata/auth-logout-response.json")
    with get_client([test_dict]) as c:
        assert c is not None


def test_custom_middlewares():
    assert_middlewares(Client())
    assert_middlewares(Client(middlewares=None))
    assert_middlewares(Client(middlewares=[]))
    assert_middlewares(Client(middlewares=[AnalysisCacheMiddleware()]))
    assert_middlewares(Client(middlewares=[ClientToolNameMiddleware()]))
    assert_middlewares(
        Client(middlewares=[AnalysisCacheMiddleware(), ClientToolNameMiddleware()])
    )
