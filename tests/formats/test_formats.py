import http
import pytest
import src.utils.validators
from tests.testutils import HEADERS, fuzz_data, invalidate_field
from ..mocks import Permissions


format_schema = {
    "id": int,
    "name": str,
    "hidden": bool,
    "map_submission_status": str,
    "run_submission_status": str,
}

full_format_schema = {
    **format_schema,
    "run_submission_wh": str | None,
    "map_submission_wh": str | None,
    "emoji": str | None,
}


@pytest.mark.formats
@pytest.mark.get
class TestGetFormats:
    async def test_formats(self, btd6ml_test_client):
        """Test getting all formats"""
        async with btd6ml_test_client.get("/formats") as resp:
            assert resp.status == http.HTTPStatus.OK, f"GET /formats returned {resp.status}"
            resp_data = await resp.json()
            assert len(resp_data) == 5, "Returned more formats than expected"
            for i, fmt in enumerate(resp_data):
                assert len(src.utils.validators.check_fields(fmt, format_schema)) == 0, \
                    f"Error while validating Format[{i}]"

    async def test_get_format(self, btd6ml_test_client, mock_auth):
        """Test getting a format successfully"""
        await mock_auth(perms={1: {Permissions.edit.config}})
        async with btd6ml_test_client.get("/formats/1", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.OK, f"GET /formats/:id returned {resp.status}"
            resp_data = await resp.json()
            assert len(src.utils.validators.check_fields(resp_data, full_format_schema)) == 0, \
                f"Error while validating the full Format data"

    async def test_get_nonexistent_format(self, btd6ml_test_client, mock_auth):
        """Test getting a format that doesn't exist"""
        await mock_auth(perms={1: {Permissions.edit.config}})
        async with btd6ml_test_client.get("/formats/9999", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, f"GET /formats/:id returned {resp.status}"

    async def test_get_format_unauthorized(self, btd6ml_test_client, mock_auth):
        """Test getting a format without providing authorization"""
        await mock_auth(unauthorized=True)

        async with btd6ml_test_client.get("/formats/1") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Getting a format with no Authorization header returns {resp.status}"

        async with btd6ml_test_client.get("/formats/1", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Getting a format with an invalid token returns {resp.status}"

    async def test_get_format_forbidden(self, btd6ml_test_client, mock_auth):
        """Test getting a format without the necessary perms"""
        await mock_auth(perms={None: Permissions.basic()})

        async with btd6ml_test_client.get("/formats/1", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Getting a format without the necessary perms returns {resp.status}"

        await mock_auth(perms={51: Permissions.mod()})
        async with btd6ml_test_client.get("/formats/1", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Getting a format without the necessary perms in that format returns {resp.status}"


@pytest.mark.formats
@pytest.mark.put
class TestEditFormats:
    @staticmethod
    def _assert_format_resp(resp_data, req_data):
        del resp_data["id"]
        del resp_data["name"]
        del resp_data["emoji"]
        del resp_data["proposed_difficulties"]
        assert resp_data == req_data, "Returned format differs from submitted one"

    async def test_edit_success(self, btd6ml_test_client, mock_auth, payload_format):
        """Test editing a format"""
        FORMAT_ID = 1
        await mock_auth(perms={FORMAT_ID: {Permissions.edit.config}})

        payload = payload_format()
        async with btd6ml_test_client.put(f"/formats/{FORMAT_ID}", headers=HEADERS, json=payload) as resp, \
                btd6ml_test_client.get(f"/formats/{FORMAT_ID}", headers=HEADERS) as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing a format with a correct payload returned {resp.status}"
            assert resp_get.status == http.HTTPStatus.OK, \
                f"Getting a format's data returned {resp_get.status}"
            self._assert_format_resp(await resp_get.json(), payload)

    async def test_edit_min(self, btd6ml_test_client, mock_auth, payload_format):
        """Test editing a format while having as many null fields as possible"""
        FORMAT_ID = 2
        await mock_auth(perms={FORMAT_ID: {Permissions.edit.config}})

        payload = {
            **payload_format(),
            "run_submission_wh": None,
            "map_submission_wh": None,
        }

        async with btd6ml_test_client.put(f"/formats/{FORMAT_ID}", headers=HEADERS, json=payload) as resp, \
                btd6ml_test_client.get(f"/formats/{FORMAT_ID}", headers=HEADERS) as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing a format with a correct payload returned {resp.status}"
            assert resp_get.status == http.HTTPStatus.OK, \
                f"Getting a format's data returned {resp_get.status}"
            self._assert_format_resp(await resp_get.json(), payload)

    async def test_unauthorized(self, btd6ml_test_client, mock_auth, payload_format, assert_state_unchanged):
        """Test editing as an unauthorized user"""
        await mock_auth(unauthorized=True)
        payload = payload_format()

        async with assert_state_unchanged("/formats"), \
                btd6ml_test_client.put("/formats/1", json=payload) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing a format with no Authorization header returns {resp.status}"

        async with assert_state_unchanged("/formats"), \
                btd6ml_test_client.put("/formats/1", headers=HEADERS, json=payload) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Submitting a completion with an invalid token returns {resp.status}"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, payload_format, assert_state_unchanged):
        """Sets all properties to every possible value, one by one"""
        await mock_auth(perms={None: Permissions.mod()})
        payload = payload_format()
        extra_expected = {
            "run_submission_wh": [None],
            "map_submission_wh": [None],
        }

        for req_data, path, sub_value in fuzz_data(payload, extra_expected):
            async with assert_state_unchanged("/formats"), \
                    btd6ml_test_client.put("/formats/1", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting {path} to {sub_value} while editing a format returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_forbidden(self, assert_state_unchanged, mock_auth, btd6ml_test_client):
        """Test editing a format without the necessary permissions"""
        await mock_auth(perms={None: Permissions.basic()})
        async with assert_state_unchanged("/formats"), \
                btd6ml_test_client.put("/formats/1", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Submitting a completion without the necessary permissions returns {resp.status}"

    async def test_submit_invalid(self, btd6ml_test_client, mock_auth, payload_format, assert_state_unchanged):
        """Test setting fields to invalid values"""
        await mock_auth(perms={None: Permissions.mod()})
        payload = payload_format()

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with assert_state_unchanged("/formats"), \
                    btd6ml_test_client.put("/formats/1", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Editing {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

        # URL fields
        validations = [("notanurl", f"a format with an invalid URL in [keypath]")]
        invalid_schema = {None: ["run_submission_wh", "map_submission_wh"]}
        for req_data, edited_path, error_msg in invalidate_field(payload, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        # Enum fields
        validations = [("notallowed", f"a format with an invalid URL in [keypath]")]
        invalid_schema = {None: ["run_submission_status", "map_submission_status"]}
        for req_data, edited_path, error_msg in invalidate_field(payload, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

