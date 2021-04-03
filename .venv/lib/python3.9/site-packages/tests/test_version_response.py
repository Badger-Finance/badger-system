import json

from mythx_models.response import VersionResponse

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/version-response.json")
OBJ_DATA = VersionResponse.from_json(JSON_DATA)


def assert_version_response(resp: VersionResponse):
    assert resp.api_version == DICT_DATA["api"]
    assert resp.maru_version == DICT_DATA["maru"]
    assert resp.mythril_version == DICT_DATA["mythril"]
    assert resp.harvey_version == DICT_DATA["harvey"]
    assert resp.hashed_version == DICT_DATA["hash"]


def test_version_response_from_valid_json():
    resp = VersionResponse.from_json(JSON_DATA)
    assert_version_response(resp)


def test_version_response_from_valid_dict():
    resp = VersionResponse.from_dict(DICT_DATA)
    assert_version_response(resp)


# def test_version_response_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         VersionResponse.from_dict({})


# def test_version_response_from_invalid_json():
#     with pytest.raises(ValidationError):
#         VersionResponse.from_json("{}")


def test_version_response_to_json():
    assert json.loads(OBJ_DATA.to_json()) == DICT_DATA


def test_version_response_to_dict():
    assert OBJ_DATA.to_dict() == DICT_DATA
