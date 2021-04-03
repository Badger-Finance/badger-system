import json

import pytest

from mythx_models.request import AuthRefreshRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/auth-refresh-request.json")
OBJ_DATA = AuthRefreshRequest.from_json(JSON_DATA)


def assert_auth_refresh_request(req: AuthRefreshRequest):
    assert req.access_token == DICT_DATA["jwtTokens"]["access"]
    assert req.refresh_token == DICT_DATA["jwtTokens"]["refresh"]
    assert req.method == "POST"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == DICT_DATA


def test_auth_refresh_request_from_valid_json():
    resp = AuthRefreshRequest.from_json(JSON_DATA)
    assert_auth_refresh_request(resp)


# def test_auth_refresh_request_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AuthRefreshRequest.from_json("{}")


def test_auth_refresh_request_from_valid_dict():
    resp = AuthRefreshRequest.from_dict(DICT_DATA)
    assert_auth_refresh_request(resp)


# def test_auth_refresh_request_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AuthRefreshRequest.from_dict({})


def test_auth_refresh_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_auth_refresh_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
