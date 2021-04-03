import json

import dateutil.parser
import pytest
from mythx_models import response as respmodels
from mythx_models.exceptions import MythXAPIError
from mythx_models.request import (
    AnalysisListRequest,
    AnalysisStatusRequest,
    AnalysisSubmissionRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    DetectedIssuesRequest,
)

from pythx.api.handler import DEFAULT_API_URL, APIHandler
from pythx.middleware.base import BaseMiddleware

from .common import get_test_case


class TestMiddleware(BaseMiddleware):
    def process_request(self, req):
        req["test"] = "test"
        return req

    def process_response(self, resp):
        resp.test = "test"
        return resp


API_HANDLER = APIHandler(middlewares=[TestMiddleware()])


def assert_request_dict_keys(d):
    assert d.get("method") is not None
    assert d.get("payload") is not None
    assert d.get("headers") is not None
    assert d.get("url") is not None
    assert d.get("params") is not None


def assert_request_dict_content(d, request_obj):
    assert d["method"] == request_obj.method
    assert d["payload"] == request_obj.payload
    assert d["headers"] == request_obj.headers
    assert d["params"] == request_obj.parameters
    assert request_obj.endpoint in d["url"]
    # check middleware request processing
    assert d["test"] == "test"


def assert_response_middleware_hook(model):
    assert model.test == "test"


@pytest.mark.parametrize(
    "request_obj",
    [
        get_test_case("testdata/analysis-list-request.json", AnalysisListRequest),
        get_test_case("testdata/detected-issues-request.json", DetectedIssuesRequest),
        get_test_case("testdata/analysis-status-request.json", AnalysisStatusRequest),
        get_test_case(
            "testdata/analysis-submission-request.json", AnalysisSubmissionRequest
        ),
        get_test_case("testdata/auth-login-request.json", AuthLoginRequest),
        get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest),
        get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest),
    ],
)
def test_request_dicts(request_obj):
    req_dict = API_HANDLER.assemble_request(request_obj)
    assert_request_dict_keys(req_dict)
    assert_request_dict_content(req_dict, request_obj)
    assert req_dict["url"].startswith(DEFAULT_API_URL)


def test_middleware_default_empty():
    assert APIHandler().middlewares == []


def assert_analysis(analysis, data):
    assert analysis.api_version == data["apiVersion"]
    assert analysis.maru_version == data["maruVersion"]
    assert analysis.mythril_version == data["mythrilVersion"]
    assert analysis.run_time == data["runTime"]
    assert analysis.queue_time == data["queueTime"]
    assert analysis.status.title() == data["status"]
    assert analysis.submitted_at == dateutil.parser.parse(data["submittedAt"])
    assert analysis.submitted_by == data["submittedBy"]
    assert analysis.uuid == data["uuid"]


def test_parse_analysis_list_response():
    test_dict = get_test_case("testdata/analysis-list-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AnalysisListResponse
    )
    assert_response_middleware_hook(model)
    for i, analysis in enumerate(model.analyses):
        response_obj = test_dict["analyses"][i]
        assert_analysis(analysis, response_obj)


def test_parse_analysis_status_response():
    test_dict = get_test_case("testdata/analysis-status-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AnalysisStatusResponse
    )
    assert_response_middleware_hook(model)
    assert_analysis(model.analysis, test_dict)


def test_parse_analysis_submission_response():
    test_dict = get_test_case("testdata/analysis-status-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AnalysisSubmissionResponse
    )
    assert_response_middleware_hook(model)
    assert model.analysis.api_version == test_dict["apiVersion"]
    assert model.analysis.maru_version == test_dict["maruVersion"]
    assert model.analysis.mythril_version == test_dict["mythrilVersion"]
    assert model.analysis.harvey_version == test_dict["harveyVersion"]
    assert model.analysis.queue_time == test_dict["queueTime"]
    assert model.analysis.status.title() == test_dict["status"]
    assert model.analysis.submitted_at == dateutil.parser.parse(
        test_dict["submittedAt"]
    )
    assert model.analysis.submitted_by == test_dict["submittedBy"]
    assert model.analysis.uuid == test_dict["uuid"]


def test_parse_detected_issues_response():
    test_dict = get_test_case("testdata/detected-issues-response.json")
    expected_report = test_dict[0]
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.DetectedIssuesResponse
    )
    assert_response_middleware_hook(model)
    assert model.issue_reports[0].issues[0].to_dict() == expected_report["issues"][0]
    assert model.issue_reports[0].source_type == expected_report["sourceType"]
    assert model.issue_reports[0].source_format == expected_report["sourceFormat"]
    assert model.issue_reports[0].source_list == expected_report["sourceList"]
    assert model.issue_reports[0].meta_data == expected_report["meta"]


def test_parse_login_response():
    test_dict = get_test_case("testdata/auth-login-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AuthLoginResponse
    )
    assert_response_middleware_hook(model)
    assert model.api_key == test_dict["jwtTokens"]["access"]
    assert model.refresh_token == test_dict["jwtTokens"]["refresh"]


def test_parse_refresh_response():
    test_dict = get_test_case("testdata/auth-refresh-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AuthRefreshResponse
    )
    assert_response_middleware_hook(model)
    assert model.access_token == test_dict["jwtTokens"]["access"]
    assert model.refresh_token == test_dict["jwtTokens"]["refresh"]


def test_parse_logout_response():
    test_dict = get_test_case("testdata/auth-logout-response.json")
    model = API_HANDLER.parse_response(
        json.dumps(test_dict), respmodels.AuthLogoutResponse
    )
    assert_response_middleware_hook(model)
    assert model.to_dict() == {}
    assert model.to_json() == "{}"


def test_send_request_successful(requests_mock):
    test_url = "mock://test.com/path"
    requests_mock.get(test_url, text="resp")
    resp = APIHandler.send_request(
        {"method": "GET", "headers": {}, "url": test_url, "payload": {}, "params": {}},
        auth_header={"Authorization": "Bearer foo"},
    )
    assert resp == "resp"
    assert requests_mock.called == 1
    h = requests_mock.request_history[0]
    assert h.method == "GET"
    assert h.url == test_url
    assert h.headers["Authorization"] == "Bearer foo"


def test_send_request_failure(requests_mock):
    test_url = "mock://test.com/path"
    requests_mock.get(test_url, text="resp", status_code=400)
    with pytest.raises(MythXAPIError):
        APIHandler.send_request(
            {
                "method": "GET",
                "headers": {},
                "url": test_url,
                "payload": {},
                "params": {},
            },
            auth_header={"Authorization": "Bearer foo"},
        )

    assert requests_mock.called == 1
    h = requests_mock.request_history[0]
    assert h.method == "GET"
    assert h.url == test_url
    assert h.headers["Authorization"] == "Bearer foo"


def test_send_request_unauthenticated(requests_mock):
    test_url = "mock://test.com/path"
    requests_mock.get("mock://test.com/path", text="resp", status_code=400)
    with pytest.raises(MythXAPIError):
        APIHandler.send_request(
            {
                "method": "GET",
                "headers": {},
                "url": test_url,
                "payload": {},
                "params": {},
            }
        )

    assert requests_mock.called == 1
    h = requests_mock.request_history[0]
    assert h.method == "GET"
    assert h.url == test_url
    assert h.headers.get("Authorization") is None
