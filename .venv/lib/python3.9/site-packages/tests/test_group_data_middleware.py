import pytest
from mythx_models.request import (
    AnalysisListRequest,
    AnalysisStatusRequest,
    AnalysisSubmissionRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    DetectedIssuesRequest,
)
from mythx_models.response import (
    AnalysisListResponse,
    AnalysisStatusResponse,
    AnalysisSubmissionResponse,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthRefreshResponse,
    DetectedIssuesResponse,
)

from pythx.middleware.group_data import GroupDataMiddleware

from .common import generate_request_dict, get_test_case

EMPTY_MIDDLEWARE = GroupDataMiddleware()
ID_ONLY_MIDDLEWARE = GroupDataMiddleware(group_id="test-id")
NAME_ONLY_MIDDLEWARE = GroupDataMiddleware(group_name="test-name")
FULL_MIDDLEWARE = GroupDataMiddleware(group_id="test-id", group_name="test-name")


@pytest.mark.parametrize(
    "middleware,request_dict,id_added,name_added",
    [
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            False,
        ),
        (
            EMPTY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            True,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            False,
        ),
        (
            ID_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            False,
            True,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            False,
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            True,
            True,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            False,
        ),
        (
            FULL_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            False,
        ),
    ],
)
def test_request_dicts(middleware, request_dict, id_added, name_added):
    new_request = middleware.process_request(request_dict)
    if id_added:
        assert new_request["payload"].get("groupId") == middleware.group_id
        del new_request["payload"]["groupId"]
    if name_added:
        assert new_request["payload"].get("groupName") == middleware.group_name
        del new_request["payload"]["groupName"]

    # rest of the result should stay the same
    assert request_dict == new_request


@pytest.mark.parametrize(
    "middleware,resp_obj",
    [
        (
            EMPTY_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            EMPTY_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            ID_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            NAME_ONLY_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            FULL_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
    ],
)
def test_response_models(middleware, resp_obj):
    new_resp_obj = middleware.process_response(resp_obj)
    assert new_resp_obj == resp_obj
