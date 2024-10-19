import pytest
import http
from ..mocks import DiscordPermRoles

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
        "users": [
            {"id": "1", "name": "usr1"},
        ],
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
    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding and editing a completion with invalid fields in the payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_fuzz(self, btd6ml_test_client, mock_discord_api):
        """Sets all properties to every possible value, one by one"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test adding and editing a completion with missing fields in the payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_discord_api):
        """Test a user adding, editing or deleting a completion if they don't have perms"""
        pytest.skip("Not Implemented")


@pytest.mark.completions
class TestEditCompletion:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion with a correct payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_admin_edit_perms(self, btd6ml_test_client, mock_discord_api):
        """Test Maplist Mods editing Expert List completions, and vice versa"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion with some missing fields"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_edit_own_completion(self, btd6ml_test_client, mock_discord_api):
        """Test editing one's own completion, or adding themselves to a completion"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_delete(self, btd6ml_test_client, mock_discord_api):
        """Test editing a completion, more than once"""
        pytest.skip("Not Implemented")
