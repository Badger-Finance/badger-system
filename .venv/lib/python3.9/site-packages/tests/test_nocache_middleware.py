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

from pythx.middleware.analysiscache import AnalysisCacheMiddleware

from .common import generate_request_dict, get_test_case

FALSE_CACHE_MIDDLEWARE = AnalysisCacheMiddleware(no_cache=False)
TRUE_CACHE_MIDDLEWARE = AnalysisCacheMiddleware(no_cache=True)


@pytest.mark.parametrize(
    "middleware,request_dict,flag_added,lookup_value",
    [
        (
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            True,
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            True,
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            True,
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
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
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            True,
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            True,
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            True,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-list-request.json", AnalysisListRequest
                )
            ),
            False,
            False,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/detected-issues-request.json", DetectedIssuesRequest
                )
            ),
            False,
            False,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case(
                    "testdata/analysis-status-request.json", AnalysisStatusRequest
                )
            ),
            False,
            False,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
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
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-login-request.json", AuthLoginRequest)
            ),
            False,
            False,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-logout-request.json", AuthLogoutRequest)
            ),
            False,
            False,
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            generate_request_dict(
                get_test_case("testdata/auth-refresh-request.json", AuthRefreshRequest)
            ),
            False,
            False,
        ),
    ],
)
def test_request_dicts(middleware, request_dict, flag_added, lookup_value):
    new_request = middleware.process_request(request_dict)
    if flag_added:
        assert new_request["payload"].get("noCacheLookup") == lookup_value
        del new_request["payload"]["noCacheLookup"]

    # rest of the result should stay the same
    assert request_dict == new_request


@pytest.mark.parametrize(
    "middleware,resp_obj",
    [
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            FALSE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case("testdata/analysis-list-response.json", AnalysisListResponse),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/detected-issues-response.json", DetectedIssuesResponse
            ),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-status-response.json", AnalysisStatusResponse
            ),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case(
                "testdata/analysis-submission-response.json", AnalysisSubmissionResponse
            ),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-login-response.json", AuthLoginResponse),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-logout-response.json", AuthLogoutResponse),
        ),
        (
            TRUE_CACHE_MIDDLEWARE,
            get_test_case("testdata/auth-refresh-response.json", AuthRefreshResponse),
        ),
    ],
)
def test_response_models(middleware, resp_obj):
    new_resp_obj = middleware.process_response(resp_obj)
    assert new_resp_obj == resp_obj
