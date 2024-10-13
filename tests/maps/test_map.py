import http
import json
import pytest
from aiohttp import FormData
from ..mocks import DiscordPermRoles

HEADERS = {"Authorization": "Bearer test_access_token"}


def map_form_data(json_data: dict) -> FormData:
    form_data = FormData()
    form_data.add_field(
        "data",
        json.dumps(json_data),
        content_type="application/json",
    )
    return form_data


@pytest.mark.maps
@pytest.mark.get
class TestGetMaps:
    async def get_map(self, btd6ml_test_client):
        """Test getting a map by code"""
        pytest.skip("Not Implemented")

    async def test_not_exists(self, btd6ml_test_client):
        """Test getting a map that doesn't exist"""
        pytest.skip("Not Implemented")

    async def test_get_by_name(self, btd6ml_test_client):
        """Test getting a map by name"""
        pytest.skip("Not Implemented")

    async def test_get_by_alias(self, btd6ml_test_client):
        """Test getting a map by an alias"""
        pytest.skip("Not Implemented")

    async def test_get_by_placement(self, btd6ml_test_client):
        """Test getting a map by its placement"""
        pytest.skip("Not Implemented")


@pytest.mark.maps
@pytest.mark.post
async def test_add(btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
    """
    Test that adding a correct map payload works, and pushes off a map off
    the list correctly and only sets the perms it can.
    """
    mock_discord_api(perms=DiscordPermRoles.ADMIN)

    cur_code = valid_codes[0]
    req_map_data = {
        **map_payload(cur_code),
        "placement_curver": 10,
        "creators": [
            {"id": "1", "role": None},
            {"id": "usr2", "role": "Suggested the idea"},
        ],
    }
    form_data = map_form_data(req_map_data)
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"POST /maps (unauthorized) returned {resp.status} " \
            f"({await resp.json() if resp.status == http.HTTPStatus.BAD_REQUEST else ''})"

    # Validate inserted data is correct
    async with btd6ml_test_client.get(f"/maps/{cur_code}") as resp:
        assert resp.status == http.HTTPStatus.OK, \
            f"GET /maps/{cur_code} returned {resp.status}"
        resp_map_data = await resp.json()

        value_eq_check = [
            "name",
            "code",
            ("placement_curver", "placement_cur"),
            ("placement_allver", "placement_all"),
            "difficulty",
            "r6_start",
            "aliases",
            "additional_codes",
            "optimal_heros",
        ]
        for key_req in value_eq_check:
            key_resp = key_req
            if isinstance(key_req, tuple):
                key_req, key_resp = key_req
            assert req_map_data[key_req] == resp_map_data[key_resp], \
                f"Map.{key_req} differs from expected"

        value_eq_check = [
            ("map_preview_url", f"https://data.ninjakiwi.com/btd6/maps/map/{cur_code}/preview"),
            ("verified", False),
            ("deleted_on", None),
            (
                "creators",
                [
                    {"id": "1", "name": "usr1", "role": None},
                    {"id": "2", "name": "usr2", "role": "Suggested the idea"},
                ]
            ),
        ]
        for key, exp_value in value_eq_check:
            assert resp_map_data[key] == exp_value, \
                f"Map.{key} differs from expected"

        no_length = ["lccs", "map_data_compatibility", "verifications"]
        for key in no_length:
            assert len(resp_map_data[key]) == 0, \
                f"Map.{key} is not an empty array"

    # Validate a map was pushed off
    async with btd6ml_test_client.get("/maps") as resp:
        maplist = await resp.json()
        assert len(maplist) == 50, \
            f"Maplist length after add: {len(maplist)}"

        for i in range(len(maplist)):
            assert maplist[i]["placement"] == i+1, \
                f"Maplist placement misordered"

    async with btd6ml_test_client.get("/maps/MLXXX50") as resp:
        assert (await resp.json())["placement_cur"] == 51, \
            "50th map was not pushed off the list"


@pytest.mark.maps
@pytest.mark.post
async def test_add_aggr_fields(btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
    """Test adding a map with all fields provided"""
    mock_discord_api(perms=DiscordPermRoles.ADMIN)

    cur_code = valid_codes[0]
    req_map_data = {
        **map_payload(cur_code),
        "placement_curver": 10,
        "creators": [
            {"id": "1", "role": None},
            {"id": "usr2", "role": "Suggested the idea"},
        ],
        "additional_codes": [
            {"code": valid_codes[1], "description": "Additional Code 1"},
            {"code": valid_codes[2], "description": "Additional Code 2"},
        ],
        "verifiers": [
            {"id": "3", "version": None},
            {"id": "usr4", "version": 441},
        ],
        "aliases": ["alias1", "alias2"],
        "version_compatibilities": [
            {"status": 2, "version": 390},
            {"status": 0, "version": 391},
        ],
        "optimal_heros": ["geraldo", "brickell"],
    }
    form_data = map_form_data(req_map_data)
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"POST /maps returned {resp.status} " \
            f"({await resp.json() if resp.status == http.HTTPStatus.BAD_REQUEST else ''})"

    # Validate inserted data is correct
    async with btd6ml_test_client.get(f"/maps/{cur_code}") as resp:
        assert resp.status == http.HTTPStatus.OK, \
            f"GET /maps/{cur_code} returned {resp.status}"

        resp_map_data = await resp.json()
        value_eq_check = [
            (
                "creators",
                [
                    {"id": "1", "name": "usr1", "role": None},
                    {"id": "2", "name": "usr2", "role": "Suggested the idea"},
                ]
            ),
            (
                "verifications",
                [
                    {"verifier": "3", "name": "usr3", "version": None},
                    {"verifier": "4", "name": "usr4", "version": 44.1},
                ]
            ),
            (
                "map_data_compatibility",
                [
                    {"status": 2, "version": 390},
                    {"status": 0, "version": 391},
                ]
            ),
            ("additional_codes", req_map_data["additional_codes"]),
            ("optimal_heros", req_map_data["optimal_heros"]),
            ("aliases", req_map_data["aliases"]),
        ]
        for key, exp_value in value_eq_check:
            assert resp_map_data[key] == exp_value, \
                f"Map.{key} differs from expected"


@pytest.mark.maps
class TestValidateMaps:
    @pytest.mark.post
    @pytest.mark.put
    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api, map_payload):
        """Test adding and editing map with invalid fields in the payload"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_req_with_images(self, btd6ml_test_client, mock_discord_api, map_payload):
        """Test adding and editing map with images in the payload works"""
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_discord_api):
        """Test a user adding, editing or deleting maps if unauthorized"""
        async def make_admin_requests(test_label: str, expected_status: int) -> None:
            TEST_CODE = "MLXXX01"

            async with btd6ml_test_client.post("/maps", headers=HEADERS) as resp:
                assert resp.status == expected_status, \
                    f"POST /maps ({test_label}) returned {resp.status}"

            async with btd6ml_test_client.put(f"/maps/{TEST_CODE}", headers=HEADERS) as resp:
                assert resp.status == expected_status, \
                    f"PUT /maps/:code ({test_label}) returned {resp.status}"

            async with btd6ml_test_client.delete(f"/maps/{TEST_CODE}", headers=HEADERS) as resp:
                assert resp.status == expected_status, \
                    f"DELETE /maps/:code ({test_label}) returned {resp.status}"

        mock_discord_api(unauthorized=True)
        await make_admin_requests("unauthorized", http.HTTPStatus.UNAUTHORIZED)

        mock_discord_api()
        await make_admin_requests("missing permissions", http.HTTPStatus.UNAUTHORIZED)


@pytest.mark.maps
class TestEditMaps:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api, map_payload):
        """
        Test editing a map with a correct payload works, and rearranging maps on
        the list correctly.
        """
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_admin_edit_perms(self, btd6ml_test_client, mock_discord_api, map_payload):
        """
        Test Maplist Mods editing Expert List attributes, and vice versa.
        """
        pytest.skip("Not Implemented")

    @pytest.mark.post
    @pytest.mark.put
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api, map_payload):
        """Test a request with some missing fields"""
        pytest.skip("Not Implemented")
