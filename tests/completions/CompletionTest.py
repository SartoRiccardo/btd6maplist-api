import http
from ..mocks import Permissions
from ..testutils import invalidate_field, fuzz_data, remove_fields

HEADERS = {"Authorization": "Bearer test_token"}


class CompletionTest:
    endpoint_path = "post"

    @staticmethod
    async def _test_invalid_fields(req_completion_data, call_endpoints):
        # User fields
        validations = [
            ("999999999", "a completion with a nonexistent user"),
            ("a", "a completion with a nonexistent username"),
        ]
        invalid_schema = {"user_ids": [0]}
        for req_data, edited_path, error_msg in invalidate_field(req_completion_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        # Non-negative fields
        validations = [(-2, f"a completion with a negative [keypath]")]
        invalid_schema = {None: ["format"], "lcc": ["leftover"]}
        for req_data, edited_path, error_msg in invalidate_field(req_completion_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        # Integer too large
        validations = [(999999, f"a completion with a [keypath] too large")]
        invalid_schema = {None: ["format"]}
        for req_data, edited_path, error_msg in invalidate_field(req_completion_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    @staticmethod
    async def _test_fuzz(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_post: str = None,
            endpoint_put: str = None,
            endpoint_get_put: str = None,
    ):
        if endpoint_get_put is None:
            endpoint_get_put = endpoint_put

        await mock_auth(perms={None: Permissions.mod()})
        req_comp_data = completion_payload()
        extra_expected = {
            "lcc": [None],
        }

        for req_data, path, sub_value in fuzz_data(req_comp_data, extra_expected):
            if endpoint_post:
                async with assert_state_unchanged(endpoint_post):
                    async with btd6ml_test_client.post(endpoint_post, headers=HEADERS, json=req_data) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Setting {path} to {sub_value} while adding a completion returns {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and path in resp_data["errors"], \
                            f"\"{path}\" was not in response.errors"

            if endpoint_put:
                async with assert_state_unchanged(endpoint_get_put):
                    async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_data) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Setting {path} to {sub_value} while editing a completion returns {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and path in resp_data["errors"], \
                            f"\"{path}\" was not in response.errors"

    @staticmethod
    async def _test_missing_fields(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_post: str = None,
            endpoint_put: str = None,
            endpoint_get_put: str = None
    ):
        if endpoint_get_put is None:
            endpoint_get_put = endpoint_put

        await mock_auth(perms={None: Permissions.mod()})
        req_comp_data = completion_payload()

        for req_data, path in remove_fields(req_comp_data):
            if endpoint_post:
                async with assert_state_unchanged(endpoint_post):
                    async with btd6ml_test_client.post(endpoint_post, headers=HEADERS, json=req_data) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Removing {path} while adding a completion returns {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and path in resp_data["errors"], \
                            f"\"{path}\" was not in response.errors"

            if endpoint_put:
                async with assert_state_unchanged(endpoint_get_put):
                    async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_data) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Removing {path} while editing a completion returns {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and path in resp_data["errors"], \
                            f"\"{path}\" was not in response.errors"

    @staticmethod
    async def _test_forbidden(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_post: str = None,
            endpoint_put: str = None,
            endpoint_get_put: str = None,
            endpoint_del: str = None,
    ):
        """Test a user adding, editing or deleting a completion if they don't have perms"""
        if endpoint_get_put is None:
            endpoint_get_put = endpoint_put
        req_comp_data = completion_payload()

        if endpoint_post:
            async with assert_state_unchanged(endpoint_post):
                await mock_auth(unauthorized=True)
                async with btd6ml_test_client.post(endpoint_post) as resp:
                    assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                        f"Adding a completion without providing authorization returns {resp.status}"
                async with btd6ml_test_client.post(endpoint_post, headers=HEADERS, json=req_comp_data) as resp:
                    assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                        f"Adding a completion with and invalid token returns {resp.status}"

                await mock_auth()
                async with btd6ml_test_client.post(endpoint_post, headers=HEADERS, json=req_comp_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Adding a completion without permissions returns {resp.status}"

        if endpoint_put:
            async with assert_state_unchanged(endpoint_get_put):
                await mock_auth(unauthorized=True)
                async with btd6ml_test_client.put(endpoint_put, json=req_comp_data) as resp:
                    assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                        f"Editing a completion without providing authorization returns {resp.status}"
                async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_comp_data) as resp:
                    assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                        f"Editing a completion with and invalid token returns {resp.status}"

                if endpoint_del:
                    async with btd6ml_test_client.delete(endpoint_del) as resp:
                        assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                            f"Deleting a completion without providing authorization returns {resp.status}"
                    async with btd6ml_test_client.delete(endpoint_del, headers=HEADERS) as resp:
                        assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                            f"Deleting a completion with and invalid token returns {resp.status}"

                await mock_auth()
                async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_comp_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Editing a completion without permissions returns {resp.status}"
                if endpoint_del:
                    async with btd6ml_test_client.delete(endpoint_del, headers=HEADERS) as resp:
                        assert resp.status == http.HTTPStatus.FORBIDDEN, \
                            f"Deleting a completion without permissions returns {resp.status}"

    @staticmethod
    async def _test_own_completion(
            btd6ml_test_client,
            mock_auth,
            assert_state_unchanged,
            completion_payload,
            endpoint_post: str = None,
            endpoint_put_own: str = None,
            endpoint_put_other: str = None,
            endpoint_get_own: str = None,
            endpoint_get_other: str = None,
    ):
        if endpoint_get_own is None:
            endpoint_get_own = endpoint_put_own
        if endpoint_get_other is None:
            endpoint_get_other = endpoint_put_other

        if endpoint_put_own:
            async with assert_state_unchanged(endpoint_get_own) as completion_og:
                completed_by = completion_og["users"][0]["id"]
                await mock_auth(perms={None: Permissions.mod()}, user_id=completed_by)

                req_data = completion_payload()
                req_data["user_ids"] = ["1"]
                async with btd6ml_test_client.put(endpoint_put_own, headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Changing one's own completion and removing oneself returns {resp.status}"

                req_data["user_ids"] = [usr["id"] for usr in completion_og["users"]]
                async with btd6ml_test_client.put(endpoint_put_own, headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Changing one's own completion while leaving users unchanged returns {resp.status}"

        if endpoint_put_other:
            async with assert_state_unchanged(endpoint_get_other):
                req_data = completion_payload()
                req_data["user_ids"].append(completed_by)
                async with btd6ml_test_client.put(endpoint_put_other, headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Adding oneself to another completion returns {resp.status}"

        if endpoint_post:
            async with assert_state_unchanged(endpoint_post):
                req_data = completion_payload()
                req_data["user_ids"].append(completed_by)
                async with btd6ml_test_client.post(endpoint_post, headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Adding oneself to another completion returns {resp.status}"

    @staticmethod
    async def _test_scoped_edit_perms(
            mock_auth,
            assert_state_unchanged,
            btd6ml_test_client,
            completion_payload,
            endpoint_put: str = None,
            endpoint_del: str = None,
            endpoint_get: str = None,
    ):
        async with assert_state_unchanged(endpoint_get) as completion:
            await mock_auth(perms={52: {"delete:completion"}})
            if endpoint_del:
                async with btd6ml_test_client.delete(endpoint_del, headers=HEADERS) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Deleting a completion without delete:completion in that format returns {resp.status}"

            await mock_auth(perms={52: {"edit:completion"}})
            req_data = completion_payload()
            async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Editing a completion without edit:completion in that format returns {resp.status}"

            req_data["format"] = completion["format"]
            async with btd6ml_test_client.put(endpoint_put, headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Editing a completion without edit:completion in that format and leaving the format unchanged " \
                    f"returns {resp.status}"
