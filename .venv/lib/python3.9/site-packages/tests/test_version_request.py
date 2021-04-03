from mythx_models.request import VersionRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/version-request.json")
OBJ_DATA = VersionRequest.from_json(JSON_DATA)


def assert_version_request(req):
    assert req.method == "GET"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}
    assert req.endpoint == "v1/version"


def test_version_request_from_valid_json():
    req = VersionRequest.from_json("{}")
    assert_version_request(req)


def test_version_request_from_valid_dict():
    req = VersionRequest.from_dict({})
    assert_version_request(req)


def test_version_request_to_json():
    assert OBJ_DATA.to_json() == "{}"


def test_version_request_to_dict():
    assert OBJ_DATA.to_dict() == {}
