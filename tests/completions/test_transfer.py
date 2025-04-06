import http
import json
import pytest
from ..mocks import Permissions
from ..testutils import fuzz_data, remove_fields

HEADERS = {
    "Authorization": "Bearer discord_token",
    "Content-Type": "application/json",
}


@pytest.mark.completions
@pytest.mark.put
class TestTransfer:
    async def test_transfer_completions(self, btd6ml_test_client, mock_auth):
        """Test transferring a map's completions to another"""
        TEST_CODE_FROM = "DELXXAC"
        TEST_CODE_TO = "MLXXXDF"

        await mock_auth(perms={None: {Permissions.edit.completion}})

        async with btd6ml_test_client.get(f"/maps/{TEST_CODE_FROM}/completions") as resp_get_from, \
                btd6ml_test_client.get(f"/maps/{TEST_CODE_TO}/completions") as resp_get_to:
            assert resp_get_from.status == http.HTTPStatus.OK, \
                f"Getting a deleted map's completions returns {resp_get_from.status}"
            old_source_comp_count = (await resp_get_from.json())["total"]
            old_target_comp_count = (await resp_get_to.json())["total"]

        async with btd6ml_test_client.put(
                f"/maps/{TEST_CODE_FROM}/completions/transfer",
                headers=HEADERS,
                data=json.dumps({"code": TEST_CODE_TO}),
        ) as resp, \
                btd6ml_test_client.get(f"/maps/{TEST_CODE_FROM}/completions") as resp_get_from, \
                btd6ml_test_client.get(f"/maps/{TEST_CODE_TO}/completions") as resp_get_to:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Transferring completions properly returns {resp.status}"
            assert (await resp_get_from.json())["total"] == 0, "Old map still has completions after transferring them"
            assert old_source_comp_count + old_target_comp_count == (await resp_get_to.json())["total"], \
                "Some old completions weren't transferred"

    async def test_transfer_perms(self, btd6ml_test_client, mock_auth):
        """Test transferring a map's completions as a Maplist/Expert mod"""
        code_from = "DELXXAG"
        code_to = "MLXXXFC"

        await mock_auth(perms={1: {Permissions.edit.completion}})
        async with btd6ml_test_client.put(
                f"/maps/{code_from}/completions/transfer",
                headers=HEADERS,
                data=json.dumps({"code": code_to}),
        ) as resp, \
                btd6ml_test_client.get(f"/maps/{code_from}/completions") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Transferring completions with edit:completion on format 1 returns {resp.status}"
            completions = (await resp_get.json())["completions"]
            for cmp in completions:
                assert cmp["format"] != 1, "Invalid format completion remaining after transfer"

        await mock_auth(perms={None: {Permissions.edit.completion}})
        async with btd6ml_test_client.put(
                f"/maps/{code_from}/completions/transfer",
                headers=HEADERS,
                data=json.dumps({"code": code_to}),
        ) as resp, \
                btd6ml_test_client.get(f"/maps/{code_from}/completions") as resp_get:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Transferring completions with edit:completion on all formats returns {resp.status}"
            assert (await resp_get.json())["total"] == 0, "Old map still has completions after transferring them"

    async def test_transfer_deleted(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test transferring a map's completions to a deleted one or from a non-deleted one"""
        TEST_TO_DEL = ("DELXXAI", "DELXXAB")
        TEST_FROM_LIVE = ("MLXXXFH", "DELXXAB")

        await mock_auth(perms={None: {Permissions.edit.completion}})

        async with assert_state_unchanged(f"/maps/{TEST_TO_DEL[0]}/completions"):
            async with btd6ml_test_client.put(
                    f"/maps/{TEST_TO_DEL[0]}/completions/transfer",
                    headers=HEADERS,
                    data=json.dumps({"code": TEST_TO_DEL[1]}),
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Transferring completions to a deleted map returns {resp.status}"

        async with assert_state_unchanged(f"/maps/{TEST_FROM_LIVE[0]}/completions"):
            async with btd6ml_test_client.put(
                    f"/maps/{TEST_FROM_LIVE[0]}/completions/transfer",
                    headers=HEADERS,
                    data=json.dumps({"code": TEST_FROM_LIVE[1]}),
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Transferring completions from a non-deleted map returns {resp.status}"

    async def test_transfer_not_exists(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """
        Test transferring a map's completions to
        or from one that doesn't exist
        """
        TEST_TO_INVALID = ("DELXXAI", "XXXXXXX")
        TEST_FROM_INVALID = ("XXXXXXX", "DELXXAI")

        await mock_auth(perms={None: {Permissions.edit.completion}})
        async with assert_state_unchanged(f"/maps/{TEST_TO_INVALID[0]}/completions"):
            async with btd6ml_test_client.put(
                    f"/maps/{TEST_TO_INVALID[0]}/completions/transfer",
                    headers=HEADERS,
                    data=json.dumps({"code": TEST_TO_INVALID[1]}),
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Transferring completions from a nonexistent map returns {resp.status}"

        async with btd6ml_test_client.put(
                f"/maps/{TEST_FROM_INVALID[0]}/completions/transfer",
                headers=HEADERS,
                data=json.dumps({"code": TEST_FROM_INVALID[1]}),
        ) as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Transferring completions to a nonexistent map returns {resp.status}"

    async def test_unauthorized(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test transferring without the correct perms"""
        TEST_FROM = "DELXXAI"

        async with assert_state_unchanged(f"/maps/{TEST_FROM}/completions"):
            await mock_auth(unauthorized=True)
            async with btd6ml_test_client.put(f"/maps/{TEST_FROM}/completions/transfer") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Transferring completions while unauthed {resp.status}"

            async with btd6ml_test_client.put(f"/maps/{TEST_FROM}/completions/transfer", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Transferring completions with an invalid token returns {resp.status}"

            await mock_auth()
            async with btd6ml_test_client.put(f"/maps/{TEST_FROM}/completions/transfer", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Transferring completions without perms returns {resp.status}"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Sets every field to another datatype, one by one"""
        TEST_FROM = "DELXXAI"

        await mock_auth(perms={None: {Permissions.edit.completion}})
        req_transfer_data = {"code": "MLXXXAA"}

        async with assert_state_unchanged(f"/maps/{TEST_FROM}/completions"):
            for req_data, path, sub_value in fuzz_data(req_transfer_data):
                async with btd6ml_test_client.put(
                        f"/maps/{TEST_FROM}/completions/transfer",
                        headers=HEADERS,
                        data=json.dumps(req_data),
                ) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting {path} to {sub_value} while transferring completions returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    async def test_missing_fields(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Tests sending the payload with some missing fields"""
        TEST_FROM = "DELXXAI"
        await mock_auth(perms={None: {Permissions.edit.completion}})
        req_transfer_data = {"code": "MLXXXAA"}

        async with assert_state_unchanged(f"/maps/{TEST_FROM}/completions"):
            for req_data, path in remove_fields(req_transfer_data):
                async with btd6ml_test_client.put(
                        f"/maps/{TEST_FROM}/completions/transfer",
                        headers=HEADERS,
                        data=json.dumps(req_data),
                ) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Removing {path} while transferring completions returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

