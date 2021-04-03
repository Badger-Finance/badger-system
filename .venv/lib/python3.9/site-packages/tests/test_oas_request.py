import pytest

from mythx_models.request import OASRequest

from .common import get_test_case

JSON_DATA, DICT_DATA = get_test_case("testdata/oas-request.json")
OBJ_DATA = OASRequest.from_json(JSON_DATA)


def assert_version_request(req):
    assert req.method == "GET"
    assert req.headers == {}
    assert req.parameters == {}
    assert req.payload == {}
    if req.mode == "html":
        assert req.endpoint == "v1/openapi"
    else:
        assert req.endpoint == "v1/openapi.yaml"


def test_oas_request_from_valid_json():
    req = OASRequest.from_json("{}")
    assert_version_request(req)


def test_oas_request_from_valid_dict():
    req = OASRequest.from_dict({})
    assert_version_request(req)


# def test_invalid_format():
#     with pytest.raises(ValidationError):
#         OASRequest(mode="invalid")


def test_oas_request_to_json():
    assert OBJ_DATA.to_json() == "{}"


def test_oas_request_to_dict():
    assert OBJ_DATA.to_dict() == {}
