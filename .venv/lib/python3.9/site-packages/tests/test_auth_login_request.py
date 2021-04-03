import json

import pytest

from mythx_models.request import AuthLoginRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/auth-login-request.json")
OBJ_DATA = AuthLoginRequest.from_json(JSON_DATA)


def assert_login(req: AuthLoginRequest):
    assert req.username == DICT_DATA["username"]
    assert req.password == DICT_DATA["password"]
    assert req.method == "POST"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == DICT_DATA


def test_login_from_valid_json():
    req = AuthLoginRequest.from_json(JSON_DATA)
    assert_login(req)


# def test_login_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AuthLoginRequest.from_json("{}")


def test_login_from_valid_dict():
    req = AuthLoginRequest.from_dict(DICT_DATA)
    assert_login(req)


# def test_login_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AuthLoginRequest.from_dict({})


def test_login_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_login_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
