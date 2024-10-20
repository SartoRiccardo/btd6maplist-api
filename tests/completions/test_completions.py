import pytest
import http
from ..mocks import DiscordPermRoles
from ..testutils import fuzz_data, remove_fields, invalidate_field

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
async def test_add(btd6ml_test_client, mock_discord_api, completion_payload):
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

    mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.FORBIDDEN, \
            f"Trying to add a Maplist-format completion as an Expert mod returns {resp.status}"
    mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD | DiscordPermRoles.MAPLIST_MOD)
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

    mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.FORBIDDEN, \
            f"Trying to add an Experts-format completion as a Maplist mod returns {resp.status}"
    mock_discord_api(perms=DiscordPermRoles.ADMIN)
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_comp_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Trying to add a Maplist-format completion as an Admin returns {resp.status}"
        async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
            resp_data = await resp_get.json()
            expected_value["created_on"] = resp_data["created_on"]
            expected_value["id"] = resp_data["id"]
            assert expected_value == resp_data


@pytest.mark.completions
class TestValidateCompletions:
    @pytest.mark.post
    @pytest.mark.put
    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api, completion_payload,
                                  assert_state_unchanged):
        """Test adding and editing a completion with invalid fields in the payload"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)
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

    @pytest.mark.post
    @pytest.mark.put
    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, completion_payload, assert_state_unchanged):
        """Sets all properties to every possible value, one by one"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)
        req_comp_data = completion_payload()
        extra_expected = {
            "lcc": [None],
        }

        for req_data, path, sub_value in fuzz_data(req_comp_data, extra_expected):
            async with assert_state_unchanged("/maps/MLXXXAA/completions"):
                async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting {path} to {sub_value} while adding a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

            async with assert_state_unchanged(f"/completions/1"):
                async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting {path} to {sub_value} while editing a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api, completion_payload,
                                  assert_state_unchanged):
        """Test adding and editing a completion with missing fields in the payload"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)
        req_comp_data = completion_payload()

        for req_data, path in remove_fields(req_comp_data):
            async with assert_state_unchanged("/maps/MLXXXAA/completions"):
                async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Removing {path} while adding a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

            async with assert_state_unchanged(f"/completions/1"):
                async with btd6ml_test_client.put("/completions/1", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Removing {path} while editing a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    @pytest.mark.post
    @pytest.mark.put
    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_discord_api, completion_payload, assert_state_unchanged):
        """Test a user adding, editing or deleting a completion if they don't have perms"""
        async with assert_state_unchanged("/maps/MLXXXAA/completions"):
            mock_discord_api(unauthorized=True)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Adding a completion without providing authorization returns {resp.status}"
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Adding a completion with and invalid token returns {resp.status}"

            mock_discord_api()
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Adding a completion without permissions returns {resp.status}"

        async with assert_state_unchanged("/completions/1"):
            mock_discord_api(unauthorized=True)
            async with btd6ml_test_client.put("/completions/1") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Editing a completion without providing authorization returns {resp.status}"
            async with btd6ml_test_client.put("/completions/1", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Editing a completion with and invalid token returns {resp.status}"

            async with btd6ml_test_client.delete("/completions/1") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Deleting a completion without providing authorization returns {resp.status}"
            async with btd6ml_test_client.delete("/completions/1", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Deleting a completion with and invalid token returns {resp.status}"

            mock_discord_api()
            async with btd6ml_test_client.put("/completions/1", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Editing a completion without permissions returns {resp.status}"
            async with btd6ml_test_client.delete("/completions/1", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Deleting a completion without permissions returns {resp.status}"

    @pytest.mark.put
    @pytest.mark.post
    async def test_own_completion(self, btd6ml_test_client, mock_discord_api, assert_state_unchanged,
                                  completion_payload):
        """Test editing one's own completion, or adding themselves to a completion"""
        comp_id = 27
        async with assert_state_unchanged(f"/completions/{comp_id}") as completion_og:
            completed_by = completion_og["users"][0]["id"]
            mock_discord_api(perms=DiscordPermRoles.ADMIN, user_id=completed_by)

            req_data = completion_payload()
            req_data["user_ids"] = ["1"]
            async with btd6ml_test_client.put(f"/completions/{comp_id}", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Changing one's own completion and removing oneself returns {resp.status}"

            req_data["user_ids"] = [usr["id"] for usr in completion_og["users"]]
            async with btd6ml_test_client.put(f"/completions/{comp_id}", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Changing one's own completion while leaving users unchanged returns {resp.status}"

        comp_id = 28
        async with assert_state_unchanged(f"/completions/{comp_id}"):
            req_data = completion_payload()
            req_data["user_ids"].append(completed_by)
            async with btd6ml_test_client.put(f"/completions/{comp_id}", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Adding oneself to another completion returns {resp.status}"

        async with assert_state_unchanged("/maps/MLXXXAA/completions"):
            req_data = completion_payload()
            req_data["user_ids"].append(completed_by)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Adding oneself to another completion returns {resp.status}"


@pytest.mark.completions
class TestEditCompletion:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion with a correct payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_admin_edit_perms(self, btd6ml_test_client, mock_discord_api, assert_state_unchanged,
                                    completion_payload):
        """Test Maplist Mods editing Expert List completions, and vice versa"""
        async def call_as_mod(perms: int, completion_id: int):
            mod_name_str = "Maplist" if perms & DiscordPermRoles.MAPLIST_MOD else "Expert"
            comp_name_str = "Expert" if perms & DiscordPermRoles.MAPLIST_MOD else "Maplist"

            mock_discord_api(perms=perms)
            async with assert_state_unchanged(f"/completions/{completion_id}") as completion:
                req_data = completion_payload()
                async with btd6ml_test_client.put(f"/completions/{completion_id}", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Editing an {comp_name_str} completion as a {mod_name_str} Mod returns {resp.status}"
                req_data["format"] = completion["format"]
                async with btd6ml_test_client.put(f"/completions/{completion_id}", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.FORBIDDEN, \
                        f"Editing an {comp_name_str} completion as a {mod_name_str} Mod while leaving the format " \
                        f"unchanged returns {resp.status}"

        await call_as_mod(DiscordPermRoles.MAPLIST_MOD, 10)
        await call_as_mod(DiscordPermRoles.EXPLIST_MOD, 17)

    @pytest.mark.delete
    async def test_delete(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion, more than once"""
        pytest.skip("Not Implemented")
