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

from pythx.middleware.toolname import ClientToolNameMiddleware

from .common import generate_request_dict, get_test_case

DEFAULT_CTN_MIDDLEWARE = ClientToolNameMiddleware()
CUSTOM_CTN_MIDDLEWARE = ClientToolNameMiddleware(name="test")


@pytest.mark.parametrize(
    "middleware,request_dict,name_added",
    [
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            True,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-submission-request.json",
                    AnalysisSubmissionRequest,
                )
            ),
            True,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
        ),
    ],
)
def test_request_dicts(middleware, request_dict, name_added):
    new_request = middleware.process_request(request_dict)
    if name_added:
        assert new_request["payload"].get("clientToolName") == middleware.name
        del new_request["payload"]["clientToolName"]

    # rest of the result should stay the same
    assert request_dict == new_request


@pytest.mark.parametrize(
    "middleware,resp_obj",
    [
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            DEFAULT_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            CUSTOM_CTN_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
    ],
)
def test_response_models(middleware, resp_obj):
    new_resp_obj = middleware.process_response(resp_obj)
    assert new_resp_obj == resp_obj
