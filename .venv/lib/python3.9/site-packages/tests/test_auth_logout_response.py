import pytest

from mythx_models.response import AuthLogoutResponse

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/auth-logout-response.json")
OBJ_DATA = AuthLogoutResponse.from_json(JSON_DATA)


def test_auth_login_response_from_valid_json():
    resp = AuthLogoutResponse.from_json("{}")
    assert type(resp) == AuthLogoutResponse


# def test_auth_login_response_from_invalid_json():
#     with pytest.raises(ValidationError):
#         AuthLogoutResponse.from_json('{"foo": "bar"}')


def test_auth_login_response_from_valid_dict():
    resp = AuthLogoutResponse.from_dict({})
    assert type(resp) == AuthLogoutResponse


# def test_auth_login_response_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         AuthLogoutResponse.from_dict({"foo": "bar"})


def test_auth_login_response_to_json():
    assert OBJ_DATA.to_json() == "{}"


def test_auth_login_response_to_dict():
    assert OBJ_DATA.to_dict() == {}
