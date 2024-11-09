import asyncio
import pytest
import http
from ..mocks import DiscordPermRoles
from .CompletionTest import CompletionTest

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.get
@pytest.mark.completions
async def test_get_completion(btd6ml_test_client):
    """Test getting a completion"""
    expected_value = {
        "id": 108,
        "map": "MLXXXAB",
        "users": [
            {"id": "45", "name": "usr45"},
            {"id": "11", "name": "usr11"},
            {"id": "1", "name": "usr1"},
        ],
        "black_border": True,
        "no_geraldo": True,
        "current_lcc": False,
        "lcc": {"leftover": 10177},
        "format": 1,
        "subm_proof_img": [
            "https://dummyimage.com/950x750/cc9966/fff",
            "https://dummyimage.com/600x400/0000ff/fff",
        ],
        "subm_proof_vid": [
            "https://youtu.be/iTvdQzJs",
            "https://youtu.be/EvzpMkyL",
        ],
        "accepted_by": "34",
        "created_on": 1728770986 + 3600 * ((108+2) % 100),
        "deleted_on": None,
        "subm_notes": None,
    }

    async with btd6ml_test_client.get("/completions/108") as resp:
        assert resp.status == http.HTTPStatus.OK, f"Getting a completion returns {resp.status}"
        assert await resp.json() == expected_value


@pytest.mark.post
@pytest.mark.completions
async def test_add(btd6ml_test_client, mock_auth, completion_payload):
    """
    Test that adding a correct completion payload works, and can only be set with the correct perms
    """
    req_comp_data = completion_payload()
    req_comp_data["format"] = 1

    expected_value = {
        "id": 0,  # Set later
        "map": "MLXXXAA",
        "users": [{"id": "1", "name": "usr1"}],
        "black_border": False,
        "no_geraldo": False,
        "current_lcc": False,
        "lcc": {"leftover": 1},
        "format": 1,
        "subm_proof_img": [],
        "subm_proof_vid": [],
        "accepted_by": "100000",
        "created_on": 0,  # Set later
        "deleted_on": None,
        "subm_notes": None,
    }

    await mock_auth(perms=DiscordPermRoles.EXPLIST_MOD)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.FORBIDDEN, \
            f"Trying to add a Maplist-format completion as an Expert mod returns {resp.status}"
    await mock_auth(perms=DiscordPermRoles.EXPLIST_MOD | DiscordPermRoles.MAPLIST_MOD)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Trying to add a Maplist-format completion as an Admin returns {resp.status}"
        async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
            resp_data = await resp_get.json()
            expected_value["created_on"] = resp_data["created_on"]
            expected_value["id"] = resp_data["id"]
            assert expected_value == resp_data

    req_comp_data = completion_payload()
    req_comp_data["format"] = 51
    expected_value["format"] = 51
    expected_value["current_lcc"] = True  # There are no format 51 LCCs

    await mock_auth(perms=DiscordPermRoles.MAPLIST_MOD)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.FORBIDDEN, \
            f"Trying to add an Experts-format completion as a Maplist mod returns {resp.status}"
    await mock_auth(perms=DiscordPermRoles.ADMIN)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Trying to add a Maplist-format completion as an Admin returns {resp.status}"
        async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
            resp_data = await resp_get.json()
            expected_value["created_on"] = resp_data["created_on"]
            expected_value["id"] = resp_data["id"]
            assert expected_value == resp_data


@pytest.mark.completions
class TestValidateCompletions(CompletionTest):
    @pytest.mark.post
    @pytest.mark.put
    async def test_invalid_fields(self, btd6ml_test_client, mock_auth, completion_payload,
                                  assert_state_unchanged):
        """Test adding and editing a completion with invalid fields in the payload"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        req_completion_data = completion_payload()

        async def call_endpoints(
                req_data: dict,
                error_path: str,
                error_msg: str = "",
        ):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with assert_state_unchanged("/maps/MLXXXAA/completions"):
                async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and error_path in resp_data["errors"], \
                        f"\"{error_path}\" was not in response.errors"
            async with assert_state_unchanged("/completions/1"):
                async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Editing {error_msg} returned {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and error_path in resp_data["errors"], \
                        f"\"{error_path}\" was not in response.errors"

        await self._test_invalid_fields(req_completion_data, call_endpoints)

    @pytest.mark.post
    @pytest.mark.put
    async def test_fuzz(self, btd6ml_test_client, mock_auth, completion_payload, assert_state_unchanged):
        """Sets all properties to every possible value, one by one"""
        await self._test_fuzz(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_post="/maps/MLXXXAA/completions",
            endpoint_put="/completions/1",
        )

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_auth, completion_payload,
                                  assert_state_unchanged):
        """Test adding and editing a completion with missing fields in the payload"""
        await self._test_missing_fields(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_post="/maps/MLXXXAA/completions",
            endpoint_put="/completions/1",
        )

    @pytest.mark.post
    @pytest.mark.put
    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test a user adding, editing or deleting a completion if they don't have perms"""
        await self._test_forbidden(
            btd6ml_test_client,
            mock_auth,
            assert_state_unchanged,
            endpoint_post="/maps/MLXXXAA/completions",
            endpoint_put="/completions/1",
            endpoint_del="/completions/1",
        )

    @pytest.mark.put
    @pytest.mark.post
    async def test_own_completion(self, btd6ml_test_client, mock_auth, assert_state_unchanged,
                                  completion_payload):
        """Test editing one's own completion, or adding themselves to a completion"""
        await self._test_own_completion(
            btd6ml_test_client,
            mock_auth,
            assert_state_unchanged,
            completion_payload,
            endpoint_post="/maps/MLXXXAA/completions",
            endpoint_put_own="/completions/27",
            endpoint_put_other="/completions/28",
        )

    @pytest.mark.put
    @pytest.mark.delete
    async def test_scoped_edit_perms(self, btd6ml_test_client, mock_auth, assert_state_unchanged,
                                     completion_payload):
        """Test Maplist Mods editing Expert List completions, and vice versa"""
        await self._test_scoped_edit_perms(
            mock_auth,
            assert_state_unchanged,
            btd6ml_test_client,
            completion_payload,
            DiscordPermRoles.MAPLIST_MOD,
            endpoint_put="/completions/10",
            endpoint_del="/completions/10",
            endpoint_get="/completions/10",
        )
        await self._test_scoped_edit_perms(
                mock_auth,
                assert_state_unchanged,
                btd6ml_test_client,
                completion_payload,
                DiscordPermRoles.EXPLIST_MOD,
                endpoint_put="/completions/17",
                endpoint_del="/completions/17",
                endpoint_get="/completions/17",
        )


@pytest.mark.completions
class TestEditCompletion:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_auth, completion_payload):
        """Test editing a completion with a correct payload"""
        req_data = completion_payload()
        req_data["lcc"] = None  # LCC tests go in ./test_leastcostchimps.py

        expected_completion = {
            "id": 1,
            "map": "MLXXXAA",
            "users": [
                {"id": "1", "name": "usr1"},
            ],
            "black_border": False,
            "no_geraldo": False,
            "current_lcc": False,
            "lcc": None,
            "format": 1,
            "subm_proof_img": [],
            "subm_proof_vid": [
                "https://youtu.be/JDwNAlvz",
                "https://youtu.be/DcNFeVto",
            ],
            "accepted_by": "35",
            "created_on": 1728770986 + 3600 * ((1+1) % 100),
            "deleted_on": None,
            "subm_notes": None,
        }

        await mock_auth(perms=DiscordPermRoles.MAPLIST_MOD)
        async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing a completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get("/completions/1") as resp_get:
                assert expected_completion == await resp_get.json(), \
                    "Modified completion differs from expected"

    @pytest.mark.delete
    async def test_delete(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test editing a completion, more than once"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        async with btd6ml_test_client.delete("/completions/17", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Deleting a completion returns {resp.status}"

        await asyncio.sleep(1)
        async with assert_state_unchanged("/completions/17"):
            async with btd6ml_test_client.delete("/completions/17", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.NO_CONTENT, \
                    f"Deleting a completion twice returns {resp.status}"

