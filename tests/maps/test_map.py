import http
import json
import copy
import pytest
import requests
from aiohttp import FormData
from ..mocks import DiscordPermRoles
from ..testutils import stringify_path, to_formdata

HEADERS = {"Authorization": "Bearer test_access_token"}


@pytest.mark.maps
@pytest.mark.get
class TestGetMaps:
    @staticmethod
    async def assert_get_correct(btd6ml_test_client, query, expected_code):
        async with btd6ml_test_client.get(f"/maps/{query}") as resp:
            assert resp.ok, \
                f"GET /maps/:code by name returned {resp.status}"
            resp_map_data = await resp.json()
            assert resp_map_data["code"] == expected_code, \
                f"GET /maps/{query} did not return {expected_code}"

    async def test_get_map(self, btd6ml_test_client):
        """Test getting a map by code"""
        async with btd6ml_test_client.get(f"/maps/MLXXXED") as resp:
            assert resp.ok, f"GET /maps/MLXXXED returned {resp.status}"
            resp_map_data = await resp.json()

            value_eq_check = {
                "name": f"Maplist Map 44",
                "code": f"MLXXXED",
                "placement_cur": 44,
                "placement_all": 39,
                "difficulty": 0,
                "r6_start": "https://drive.google.com/file/d/qWpmWHvTUJMEhyxBNiZTsMJjOHJfLFdY/view",
                "map_data": None,
                "optimal_heros": ["rosalia", "geraldo"],
                "map_preview_url": "https://dummyimage.com/250x150/9966cc/fff",
                "verified": True,
                "deleted_on": None,
                "creators": [
                    {"id": "12", "name": "usr12", "role": "Decoration"},
                    {"id": "30", "name": "usr30", "role": "Gameplay"},
                ],
                "additional_codes": [{"code": "MLA1X44", "description": "Additional Code 1"}],
                "verifications": [
                    {"verifier": "10", "name": "usr10", "version": None},
                    {"verifier": "12", "name": "usr12", "version": None},
                    {"verifier": "10", "name": "usr10", "version": 44.1},
                    {"verifier": "12", "name": "usr12", "version": 44.1},
                ],
            }
            for key in value_eq_check:
                exp_value = value_eq_check[key]
                assert resp_map_data[key] == exp_value, \
                    f"Map.{key} differs from expected"

    async def test_not_exists(self, btd6ml_test_client):
        """Test getting a map that doesn't exist"""
        async with btd6ml_test_client.get(f"/maps/AAAAAAA") as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"GET /maps/:code on a nonexistent map returned {resp.status}"

    async def test_get_by_name(self, btd6ml_test_client):
        """Test getting a map by name"""
        await self.assert_get_correct(btd6ml_test_client, "Maplist Map 45", "MLXXXEE")
        await self.assert_get_correct(btd6ml_test_client, "Deleted Maplist Map 9", "DELXXAJ")

    async def test_get_by_alias(self, btd6ml_test_client):
        """Test getting a map by an alias, checking priority over deleted map's names"""
        await self.assert_get_correct(btd6ml_test_client, "ml45", "MLXXXEE")
        await self.assert_get_correct(btd6ml_test_client, "deleted maplist map 0", "MLXXXEE")

    async def test_get_by_placement(self, btd6ml_test_client):
        """Test getting a map by its placement"""
        await self.assert_get_correct(btd6ml_test_client, "45", "MLXXXEE")
        await self.assert_get_correct(btd6ml_test_client, "@5", "MLXXXAJ")


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
    form_data = to_formdata(req_map_data)
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"POST /maps (unauthorized) returned {resp.status} " \
            f"({await resp.json() if resp.status == http.HTTPStatus.BAD_REQUEST else ''})"

    # Validate inserted data is correct
    async with btd6ml_test_client.get(f"/maps/{cur_code}") as resp:
        assert resp.status == http.HTTPStatus.OK, \
            f"GET /maps/{cur_code} returned {resp.status}"
        resp_map_data = await resp.json()

        value_eq_check = {
            "name": req_map_data["name"],
            "code": req_map_data["code"],
            "placement_cur": req_map_data["placement_curver"],
            "placement_all": req_map_data["placement_allver"],
            "difficulty": req_map_data["difficulty"],
            "r6_start": req_map_data["r6_start"],
            "aliases": req_map_data["aliases"],
            "additional_codes": req_map_data["additional_codes"],
            "optimal_heros": req_map_data["optimal_heros"],
            "map_preview_url": f"https://data.ninjakiwi.com/btd6/maps/map/{cur_code}/preview",
            "verified": False,
            "deleted_on": None,
            "creators": [
                {"id": "1", "name": "usr1", "role": None},
                {"id": "2", "name": "usr2", "role": "Suggested the idea"},
            ],
        }
        for key in value_eq_check:
            exp_value = value_eq_check[key]
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

    async with btd6ml_test_client.get("/maps/MLXXXEJ") as resp:
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
    form_data = to_formdata(req_map_data)
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
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


@pytest.mark.put
@pytest.mark.post
@pytest.mark.maps
class TestValidateMaps:
    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
        """Sets every field to another datatype, one by one"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)
        req_map_data = {
            **map_payload(valid_codes[0]),
            "placement_curver": 1,
            "placement_allver": 1,
            "creators": [{"id": "1", "role": None}],
            "additional_codes": [{"code": valid_codes[1], "description": "Additional Code 1"}],
            "verifiers": [{"id": "3", "version": None}],
            "aliases": ["alias1", "alias2"],
            "version_compatibilities": [{"status": 2, "version": 390}],
            "optimal_heros": ["geraldo", "brickell"],
        }
        extra_expected = {
            "map_data": [str],
            "r6_start": [str],
            "map_preview_url": [str],
            "creators": {"role": [str]},
            "verifiers": {"version": [float]},
        }
        test_values = [[], {}, 1.7, "a", None]

        async def send_request(key_path: list):
            request_data = copy.deepcopy(req_map_data)
            current_data = request_data
            extra_types = extra_expected
            for i, key in enumerate(key_path):
                if isinstance(key, str) and isinstance(extra_types, dict) and key in extra_types:
                    extra_types = extra_types[key]
                if i < len(key_path)-1:
                    current_data = current_data[key]

            original_type = current_data[key_path[-1]].__class__
            for dtype in test_values:
                if isinstance(extra_types, list) and dtype.__class__ in extra_types or \
                        dtype.__class__ == original_type:
                    continue
                current_data[key_path[-1]] = dtype
                form_data = to_formdata(request_data)
                async with btd6ml_test_client.put("/maps/MLXXXAB", headers=HEADERS, data=form_data) as resp:
                    error_path = stringify_path(key_path)
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting Map.{error_path} to {dtype} while editing a map returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and error_path in resp_data["errors"], \
                        f"\"{error_path}\" was not in response.errors"

        async def fuzz_request(current_path: list = None):
            if current_path is None:
                current_path = []
            current_data = req_map_data
            for key in current_path:
                current_data = current_data[key]

            if len(current_path) > 0:
                await send_request(current_path)
            if isinstance(current_data, dict):
                for key in current_data:
                    current_path.append(key)
                    await fuzz_request(current_path)
                    current_path.pop()
            elif isinstance(current_data, list):
                current_path.append(0)
                await fuzz_request(current_path)
                current_path.pop()

        await fuzz_request()

    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
        """Test adding and editing map with invalid fields in the payload"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_map_data = {
            **map_payload(valid_codes[3]),
            "placement_curver": 1,
            "placement_allver": 1,
            "creators": [{"id": "1", "role": None}],
            "additional_codes": [{"code": valid_codes[2], "description": "Additional Code 1"}],
            "verifiers": [{"id": "3", "version": None}],
            "aliases": ["alias1", "alias2"],
            "version_compatibilities": [{"status": 2, "version": 390}],
            "optimal_heros": ["geraldo", "brickell"],
        }

        async def invalidate_field(schema: dict | list, test_func, current_path: list = None):
            if current_path is None:
                current_path = []

            if isinstance(schema, dict):
                for key in schema:
                    if key is not None:
                        current_path.append(key)
                    await invalidate_field(schema[key], test_func, current_path)
                    if key is not None:
                        current_path.pop()
            elif isinstance(schema, list):
                for key in schema:
                    appended = 1
                    request_data = copy.deepcopy(req_map_data)
                    current_data = request_data
                    for i, path_key in enumerate(current_path):
                        while isinstance(current_data, list):
                            appended += 1
                            current_path.append(0)
                            current_data = current_data[0]
                        current_data = current_data[path_key]
                    while isinstance(current_data, list):
                        appended += 1
                        current_path.append(0)
                        current_data = current_data[0]
                    current_path.append(key)
                    await test_func(request_data, current_data, key, current_path)
                    for _ in range(appended):
                        current_path.pop()

        async def call_endpoints(
                validations: list[tuple],
                full_data: dict,
                edit: dict,
                key: str,
                key_path: list,
                test_edit: bool = True,
                test_add: bool = True,
        ):
            error_path = stringify_path(key_path)
            for test_val, error_msg in validations:
                edit[key] = test_val
                if test_add:
                    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(full_data)) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned %d" % resp.status
                        resp_data = await resp.json()
                        assert "errors" in resp_data and error_path in resp_data["errors"], \
                            f"\"{error_path}\" was not in response.errors"
                if test_edit:
                    async with btd6ml_test_client.put("/maps/MLXXXEI", headers=HEADERS, data=to_formdata(full_data)) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Editing {error_msg} returned %d" % resp.status
                        resp_data = await resp.json()
                        assert "errors" in resp_data and error_path in resp_data["errors"], \
                            f"\"{error_path}\" was not in response.errors"

        async def assert_codes(full_data: dict, edit: dict, key: str, key_path: list):
            validations = [
                ("AAAAAAA", "a map with a nonexistent code does not returns %d"),
                ("AAAAAA1", "a map with an invalid code does not returns %d"),
                ("AAAAAAAA", "a map with an invalid code does not returns %d"),
                ("MLXXXEJ", "a map with an already inserted map does not returns %d"),
            ]
            await call_endpoints(validations, full_data, edit, key, key_path, test_edit=stringify_path(key_path) != "code")
        await invalidate_field(
            {None: ["code"], "additional_codes": ["code"]},
            assert_codes,
        )

        async def assert_users(*args):
            validations = [
                ("999999999", "a map with a nonexistent user"),
                ("a", "a map with a non-numeric user"),
            ]
            await call_endpoints(validations, *args)
        await invalidate_field(
            {"creators": ["id"], "verifiers": ["id"]},
            assert_users,
        )

        async def assert_string_fields(full_data: dict, edit: dict, key: str, key_path: list):
            error_path = stringify_path(key_path)
            validations = [
                ("", f"a map with an empty {error_path}"),
                ("a"*1000, f"a map with a {error_path} too long"),
            ]
            await call_endpoints(validations, full_data, edit, key, key_path)
        await invalidate_field(
            {
                None: ["name", "r6_start", "map_preview_url"],
                "additional_codes": ["description"],
                "creators": ["role"],
            },
            assert_string_fields,
        )

        async def assert_non_neg_fields(full_data: dict, edit: dict, key: str, key_path: list):
            # -1 is a special value so that would be valid
            error_path = stringify_path(key_path)
            validations = [(-2, f"a map with a negative {error_path}")]
            await call_endpoints(validations, full_data, edit, key, key_path)
        await invalidate_field(
            {None: ["placement_curver", "placement_allver", "difficulty"]},
            assert_non_neg_fields,
        )

        async def assert_int_too_big(full_data: dict, edit: dict, key: str, key_path: list):
            error_path = stringify_path(key_path)
            validations = [(999999, f"a map with a {error_path} too large")]
            await call_endpoints(validations, full_data, edit, key, key_path)
        await invalidate_field(
            {None: ["difficulty"]},
            assert_int_too_big,
        )

    async def test_req_with_images(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes, tmp_path):
        """Test adding and editing map with images in the payload works"""
        async def assert_images(code: str, expected: tuple[str, str], full: bool = False):
            async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                resp_data = await resp_get.json()
                check_url = resp_data["r6_start"] if full else resp_data["r6_start"].split("/")[-1]
                assert check_url == expected[0], "Map.r6_start differs from expected"
                check_url = resp_data["map_preview_url"] if full else resp_data["map_preview_url"].split("/")[-1]
                assert check_url == expected[1], "Map.map_preview_url differs from expected"

        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        image_urls = [
            "https://dummyimage.com/400x300/00ff00/000",
            "https://dummyimage.com/600x400/0000ff/fff",
        ]
        for i, url in enumerate(image_urls):
            path = tmp_path / f"image{i}.png"
            path.write_bytes(requests.get(url).content)

        req_map_data = {
            **map_payload(valid_codes[0]),
            "difficulty": 0,
            "creators": [{"id": "1", "role": None}],
        }
        form_data = to_formdata(req_map_data)
        form_data.add_field("r6_start", (tmp_path/"image0.png").open("rb"))
        form_data.add_field("map_preview_url", (tmp_path/"image1.png").open("rb"))
        async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
            assert resp.ok, f"Adding a map with images in the payload return {resp.status}"
            await assert_images(
                valid_codes[0], (
                    "e7e2636a87ed7a754d01379a2412beeab09df53918a56701762b6344715650ea.png",
                    "4a611bb64cbe70ed3878a6101422dd0f3c33a95dd8f892f75df4a5cd5000d884.png"
                )
            )

        form_data = to_formdata(req_map_data)
        form_data.add_field("r6_start", (tmp_path/"image0.png").open("rb"))
        form_data.add_field("map_preview_url", (tmp_path/"image1.png").open("rb"))
        async with btd6ml_test_client.put(f"/maps/{valid_codes[0]}", headers=HEADERS, data=form_data) as resp:
            assert resp.ok, f"Editing a map with images in the payload return {resp.status}"
            await assert_images(
                valid_codes[0], (
                    "e7e2636a87ed7a754d01379a2412beeab09df53918a56701762b6344715650ea.png",
                    "4a611bb64cbe70ed3878a6101422dd0f3c33a95dd8f892f75df4a5cd5000d884.png"
                )
            )

        form_data = to_formdata({
            **req_map_data,
            "r6_start": "https://example.com/img1.png",
            "map_preview_url": "https://example.com/img2.png",
        })
        form_data.add_field("r6_start", (tmp_path/"image0.png").open("rb"))
        form_data.add_field("map_preview_url", (tmp_path/"image1.png").open("rb"))
        async with btd6ml_test_client.put(f"/maps/{valid_codes[0]}", headers=HEADERS, data=form_data):
            assert resp.ok, f"Editing a map with images in the payload and json body return {resp.status}"
            await assert_images(
                valid_codes[0], ("https://example.com/img1.png", "https://example.com/img2.png"), full=True
            )

        form_data = to_formdata({
            **req_map_data,
            "code": valid_codes[1],
            "r6_start": "https://example.com/img1.png",
            "map_preview_url": "https://example.com/img2.png",
        })
        form_data.add_field("r6_start", (tmp_path/"image0.png").open("rb"))
        form_data.add_field("map_preview_url", (tmp_path/"image1.png").open("rb"))
        async with btd6ml_test_client.post(f"/maps", headers=HEADERS, data=form_data):
            assert resp.ok, f"Adding a map with images in the payload and json body return {resp.status}"
            await assert_images(
                valid_codes[1], ("https://example.com/img1.png", "https://example.com/img2.png"), full=True
            )

    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
        """Test a request with some missing fields"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        correct_map_data = {
            **map_payload("MLXXXCJ"),
            "difficulty": 0,
            "creators": [{"id": "1", "role": None}],
            "additional_codes": [{"code": valid_codes[1], "description": "Additional Code 1"}],
            "verifiers": [{"id": "3", "version": None}],
            "version_compatibilities": [{"status": 2, "version": 390}],
        }
        for key in correct_map_data:
            req_map_data = {**correct_map_data}
            del req_map_data[key]
            async with btd6ml_test_client.put("/maps/MLXXXCJ", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Removing Map.{key} from editing a map resulted in code {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and key in resp_data["errors"], \
                    f"{key} not in errors"

            req_map_data = {
                **correct_map_data,
                "code": valid_codes[0],
            }
            del req_map_data[key]
            async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Removing Map.{key} from adding a map resulted in code {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and key in resp_data["errors"], \
                    f"{key} not in errors"

            # Can do this recursively but not worth it for this
            if isinstance(correct_map_data[key], list) and len(correct_map_data[key]):
                for inner_key in correct_map_data[key][0]:
                    req_map_data = {
                        **correct_map_data,
                        key: [{**obj} for obj in correct_map_data[key]],
                    }
                    del req_map_data[key][0][inner_key]
                    async with btd6ml_test_client.put("/maps/MLXXXCJ", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Removing Map.{key}[0].{inner_key} from editing a map resulted in code {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and f"{key}[0].{inner_key}" in resp_data["errors"], \
                            f"{key}[0].{inner_key} not in errors"

                    req_map_data = {
                        **correct_map_data,
                        key: [{**obj} for obj in correct_map_data[key]],
                        "code": valid_codes[0],
                    }
                    del req_map_data[key][0][inner_key]
                    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Removing Map.{key}[0].{inner_key} from adding a map resulted in code {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and f"{key}[0].{inner_key}" in resp_data["errors"], \
                            f"{key}[0].{inner_key} not in errors"

    async def test_moderator_perms(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
        """
        Test Maplist Mods adding and editing Expert List attributes, and vice versa.
        """
        async def assert_map_placements(map_code: str, expected: tuple[int, int, int], mod_type: str):
            async with btd6ml_test_client.get(f"/maps/{map_code}") as resp:
                resp_map_data = await resp.json()
                assert resp_map_data["placement_cur"] == expected[0], \
                    f"{mod_type} Moderator {'did not change' if mod_type == 'Maplist' else 'changed'} List Placement"
                assert resp_map_data["placement_all"] == expected[1], \
                    f"{mod_type} Moderator {'did not change' if mod_type == 'Maplist' else 'changed'} List Placement"
                assert resp_map_data["difficulty"] == expected[2], \
                    f"{mod_type} Moderator {'did not change' if mod_type != 'Maplist' else 'changed'} Expert Difficulty"

        test_code = valid_codes[0]
        req_map_data = {
            **map_payload(test_code),
            "placement_curver": 10,
            "placement_allver": 10,
            "difficulty": 2,
            "creators": [{"id": "1", "role": None}],
        }

        # Maplist Mods
        mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)
        async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"POST /maps/{test_code} returned {resp.status}"

        async with btd6ml_test_client.put("/maps/MLXXXAA", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
            assert resp.ok, f"PUT /maps/MLXXXAA returned {resp.status}"
            await assert_map_placements("MLXXXAA", (10, 10, -1), "Maplist")

        # Expert Mods
        mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD)
        async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"POST /maps/{test_code} returned {resp.status}"

        async with btd6ml_test_client.put("/maps/MLXXXAB", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
            assert resp.ok, f"PUT /maps/MLXXXAB returned {resp.status}"
            await assert_map_placements("MLXXXAB", (1, -1, 2), "Experts")

    @pytest.mark.delete
    async def test_forbidden(self, btd6ml_test_client, mock_discord_api):
        """Test a user adding, editing or deleting maps if unauthorized"""
        async def make_admin_requests(test_label: str, expected_status: int) -> None:
            TEST_CODE = "MLXXXAA"

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
        await make_admin_requests("missing permissions", http.HTTPStatus.FORBIDDEN)


@pytest.mark.maps
class TestEditMaps:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
        """
        Test editing a map with a correct payload works, and rearranging maps on
        the list correctly.
        """
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_map_data = {
            **map_payload("MLXXXCJ"),  # 30th map
            "placement_curver": 30,
            "placement_allver": 30,
            "difficulty": 2,
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
                {"id": "usr4", "version": 440},
                {"id": "4", "version": None},
            ],
            "aliases": ["alias1", "alias2"],
            "version_compatibilities": [
                {"status": 0, "version": 400},
                {"status": 2, "version": 401},
            ],
            "optimal_heros": ["geraldo", "brickell"],
        }

        async with btd6ml_test_client.put("/maps/MLXXXCJ", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
            assert resp.ok, f"PUT /maps/MLXXXCJ returned {resp.status}"

        async with btd6ml_test_client.get("/maps/MLXXXCJ") as resp:
            resp_map_data = await resp.json()
            value_eq_check = {
                **req_map_data,
                "map_data_compatibility": [
                    {"status": 3, "version": 390},
                    {"status": 0, "version": 400},
                    {"status": 2, "version": 401},
                ],
                "verifications": [
                    {"verifier": "3", "name": "usr3", "version": None},
                    {"verifier": "4", "name": "usr4", "version": None},
                    {"verifier": "4", "name": "usr4", "version": 44.1},
                ],
                "creators": [
                    {"id": "1", "name": "usr1", "role": None},
                    {"id": "2", "name": "usr2", "role": "Suggested the idea"},
                ],
                "map_preview_url": f"https://data.ninjakiwi.com/btd6/maps/map/MLXXXCJ/preview",
                "verified": True,
                "placement_all": req_map_data["placement_allver"],
                "placement_cur": req_map_data["placement_curver"],
            }
            del value_eq_check["code"]
            del value_eq_check["placement_allver"]
            del value_eq_check["placement_curver"]
            del value_eq_check["verifiers"]
            del value_eq_check["version_compatibilities"]
            for key in value_eq_check:
                assert resp_map_data[key] == value_eq_check[key], \
                    f"PUT /maps/MLXXXAA Map.{key} differs from expected"

    @pytest.mark.delete
    async def test_delete(self, btd6ml_test_client, mock_discord_api):
        """Test deleting a map, and all other maps rearranging"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        last_map = "MLXXXEJ"
        async with btd6ml_test_client.delete(f"/maps/{last_map}", headers=HEADERS) as resp:
            assert resp.ok, f"Delete map with correct perms returned {resp.status}"
            async with btd6ml_test_client.get(f"/maps/{last_map}") as resp_get:
                assert resp_get.ok, f"Get deleted map returned {resp.status}"
                resp_map_data = await resp_get.json()
                assert resp_map_data["deleted_on"] is not None, \
                    f"Map.deleted_on is not None after being deleted"

                current_deleted_on = resp_map_data["deleted_on"]
                async with btd6ml_test_client.delete(f"/maps/{last_map}", headers=HEADERS) as resp_delete_again:
                    assert resp_delete_again.status == http.HTTPStatus.NO_CONTENT, \
                        f"Deleting a map again returns {resp_delete_again.status}"
                async with btd6ml_test_client.get(f"/maps/{last_map}") as resp_get_again:
                    resp_del_data = await resp_get_again.json()
                    assert current_deleted_on == resp_del_data["deleted_on"], \
                        "Map.deleted_on changed upon double deletion"

            async with btd6ml_test_client.get(f"/maps/50") as resp_get:
                resp_map_data = await resp_get.json()
                assert resp_map_data["code"] == "MLXXXFA", "Last map is not the expected one"

    @pytest.mark.delete
    async def test_delete_missing_perms(self, btd6ml_test_client, mock_discord_api):
        """Test deleting a map without having the perms to delete it completely"""
        async def delete_gradually(code: str, prev_values: tuple[int, int, int], maplist_first: bool):
            mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD if maplist_first else DiscordPermRoles.EXPLIST_MOD)
            async with btd6ml_test_client.delete(f"/maps/{code}", headers=HEADERS) as resp:
                assert resp.ok, f"Deleting a map with correct perms returned {resp.status}"
                async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                    resp_map_data = await resp_get.json()
                    assert resp_map_data["deleted_on"] is None, "Map.deleted_on is not None after partial deletion"
                    assert resp_map_data["placement_cur"] == (-1 if maplist_first else prev_values[0]), \
                        "Map.placement_cur != -1 after deletion"
                    assert resp_map_data["placement_all"] == (-1 if maplist_first else prev_values[1]), \
                        "Map.placement_all != -1 after deletion"
                    assert resp_map_data["difficulty"] == (prev_values[2] if maplist_first else -1), \
                        "Map.difficulty changed after deletion by Maplist Mod"

            mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD if maplist_first else DiscordPermRoles.MAPLIST_MOD)
            async with btd6ml_test_client.delete(f"/maps/{code}", headers=HEADERS) as resp:
                assert resp.ok, f"Deleting a map with correct perms returned {resp.status}"
                async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                    resp_map_data = await resp_get.json()
                    assert resp_map_data["deleted_on"] is not None, "Map.deleted_on is None after remaining deletion"
                    assert resp_map_data["placement_cur"] == -1, "Map.placement_cur != -1 after full deletion"
                    assert resp_map_data["placement_all"] == -1, "Map.placement_all != -1 after full deletion"
                    assert resp_map_data["difficulty"] == -1, "Map.difficulty != -1 after full deletion"

        await delete_gradually("MLXXXDJ", (40, 35, 0), True)
        await delete_gradually("MLXXXEA", (40, 35, 0), False)

    @pytest.mark.put
    async def test_edit_legacy_map(self, btd6ml_test_client, mock_discord_api, map_payload):
        """Test editing a legacy map fails. It only succeeds if leaving the placements untouched"""
        """Test adding aliases to a map reclaimed them from a deleted one"""
        async def assert_legacy_role(code, uid, placement):
            async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                resp_map_data = await resp_get.json()
                assert resp_map_data["creators"] == [{"id": str(uid), "role": "Legacy Role", "name": f"usr{uid}"}], \
                    "Legacy map not edited correctly"
                assert resp_map_data["placement_cur"] == placement, \
                    "Legacy placement was changed"

        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        async with btd6ml_test_client.get("/maps/55") as resp:
            code = (await resp.json())["code"]

        req_map_data = {
            **map_payload(code),
            "placement_curver": 55,
            "creators": [{"id": "1", "role": "Legacy Role"}],
        }
        form_data = to_formdata(req_map_data)
        async with btd6ml_test_client.put(f"/maps/{code}", headers=HEADERS, data=form_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing legacy map with same placement returned {resp.status}"
            await assert_legacy_role(code, 1, 55)

        req_map_data = {
            **req_map_data,
            "placement_curver": 51,
            "creators": [{"id": "2", "role": "Legacy Role"}],
        }
        form_data = to_formdata(req_map_data)
        async with btd6ml_test_client.put(f"/maps/{code}", headers=HEADERS, data=form_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing legacy map with different placement returned {resp.status}"
            await assert_legacy_role(code, 2, 55)

    @pytest.mark.put
    @pytest.mark.post
    async def test_reassign_aliases(self, btd6ml_test_client, mock_discord_api, map_payload):
        """Test adding aliases to a map reclaimed them from a deleted one"""
        mock_discord_api(perms=DiscordPermRoles.ADMIN)

        req_map_data = {
            **map_payload("MLXXXDF"),
            "difficulty": 0,
            "creators": [{"id": "1", "role": None}],
            "aliases": ["deleted_map_alias1"],
        }
        form_data = to_formdata(req_map_data)
        async with btd6ml_test_client.put("/maps/MLXXXDF", headers=HEADERS, data=form_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Editing map with deleted map's alias returned {resp.status}"
            async with btd6ml_test_client.get("/maps/MLXXXDF") as resp_get:
                resp_map_data = await resp_get.json()
                assert resp_map_data["aliases"] == ["deleted_map_alias1"], \
                    "Map.aliases differs from expected when adding deleted map's alias"
            async with btd6ml_test_client.get("/maps/DELXXAB") as resp_get:
                resp_map_data = await resp_get.json()
                assert resp_map_data["aliases"] == ["other_deleted_map_alias1"], \
                    "Deleted alias still in old map's data"


@pytest.mark.put
@pytest.mark.post
@pytest.mark.maps
async def test_large_placements(btd6ml_test_client, mock_discord_api, map_payload, valid_codes):
    """Test adding/editing a map with a really large placement"""
    mock_discord_api(perms=DiscordPermRoles.ADMIN)

    req_map_data = {
        **map_payload(valid_codes[0]),
        "placement_curver": 99999,
        "placement_allver": 99999,
        "creators": [{"id": "1", "role": None}],
    }
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Adding map with large placements returns {resp.status}"
        async with btd6ml_test_client.get(f"/maps/{valid_codes[0]}") as resp_get:
            resp_map_data = await resp_get.json()
            assert resp_map_data["placement_cur"] == -1, \
                "Map.placement_cur != -1 when added with a large payload"
            assert resp_map_data["placement_all"] == -1, \
                "Map.placement_all != -1 when added with a large payload"

    async with btd6ml_test_client.get(f"/maps/MLXXXAA") as resp_get:
        prev_map_data = await resp_get.json()
    async with btd6ml_test_client.put("/maps/MLXXXAA", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"Adding map with large placements returns {resp.status}"
        async with btd6ml_test_client.get(f"/maps/MLXXXAA") as resp_get:
            resp_map_data = await resp_get.json()
            assert resp_map_data["placement_cur"] == prev_map_data["placement_cur"], \
                "Map.placement_cur != -1 when added with a large payload"
            assert resp_map_data["placement_all"] == prev_map_data["placement_all"], \
                "Map.placement_all != -1 when added with a large payload"

    mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
            f"Adding map with large placements as a list moderator returns {resp.status}"
