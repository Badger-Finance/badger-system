import json

import pytest

from mythx_models.request import AuthLogoutRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/auth-logout-request.json")
OBJ_DATA = AuthLogoutRequest.from_json(JSON_DATA)


def assert_logout_request(req):
    assert req.global_ == DICT_DATA["global"]
    assert req.method == "POST"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}


def test_auth_logout_request_from_valid_json():
    req = AuthLogoutRequest.from_json(JSON_DATA)
    assert_logout_request(req)


# def test_auth_logout_request_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AuthLogoutRequest.from_json("{}")


def test_auth_logout_request_from_valid_dict():
    req = AuthLogoutRequest.from_dict(DICT_DATA)
    assert_logout_request(req)


# def test_auth_logout_request_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AuthLogoutRequest.from_dict({})


def test_auth_logout_request_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_auth_logout_request_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
