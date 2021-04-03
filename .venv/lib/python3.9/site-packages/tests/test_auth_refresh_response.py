import json

import pytest

from mythx_models.response import AuthRefreshResponse

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/auth-refresh-response.json")
OBJ_DATA = AuthRefreshResponse.from_json(JSON_DATA)


def assert_auth_refresh_response(resp: AuthRefreshResponse):
    assert resp.access_token == DICT_DATA["jwtTokens"]["access"]
    assert resp.refresh_token == DICT_DATA["jwtTokens"]["refresh"]


def test_auth_refresh_response_from_valid_json():
    resp = AuthRefreshResponse.from_json(JSON_DATA)
    assert_auth_refresh_response(resp)


# def test_auth_refresh_response_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AuthRefreshResponse.from_json("{}")


def test_auth_refresh_response_from_valid_dict():
    resp = AuthRefreshResponse.from_dict(DICT_DATA)
    assert_auth_refresh_response(resp)


# def test_auth_refresh_response_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AuthRefreshResponse.from_dict({})


def test_auth_refresh_response_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_auth_refresh_response_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
