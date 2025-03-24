import http
import pytest
from ..mocks import Permissions
from ..testutils import to_formdata, fuzz_data, invalidate_field

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
                "placement_curver": 44,
                "placement_allver": 39,
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

            lcc_ids = set()
            for lcc in resp_map_data["lccs"]:
                assert lcc["id"] not in lcc_ids, "Found duplicate LCC completion"
                lcc_ids.add(lcc["id"])

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
async def test_add(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """
    Test that adding a correct map payload works, and pushes off a map off
    the list correctly and only sets the perms it can.
    """
    await mock_auth(perms={1: {Permissions.create.map}})

    cur_code = valid_codes[0]
    req_map_data = {
        **map_payload(cur_code, []),
        "placement_curver": 10,
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
            "placement_curver": req_map_data["placement_curver"],
            "placement_allver": req_map_data["placement_allver"],
            "difficulty": req_map_data["difficulty"],
            "r6_start": req_map_data["r6_start"],
            "aliases": req_map_data["aliases"],
            "additional_codes": req_map_data["additional_codes"],
            "optimal_heros": req_map_data["optimal_heros"],
            "map_preview_url": f"https://data.ninjakiwi.com/btd6/maps/map/{cur_code}/preview",
            "verified": False,
            "deleted_on": None,
            "creators": [],
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
        assert (await resp.json())["placement_curver"] == 51, \
            "50th map was not pushed off the list"


@pytest.mark.maps
@pytest.mark.post
async def test_add_aggr_fields(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """Test adding a map with all fields provided"""
    await mock_auth(perms={1: {Permissions.create.map}})

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
async def test_fuzz(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """Sets every field to another datatype, one by one"""
    await mock_auth(perms={1: Permissions.curator(), 2: Permissions.curator()})
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
        "placement_curver": [None],
        "placement_allver": [None],
        "difficulty": [None],
        "botb_difficulty": [None],
        "map_data": [str],
        "r6_start": [str],
        "map_preview_url": [str],
        "creators": {"role": [str]},
        "verifiers": {"version": [float]},
    }

    for req_data, path, sub_value in fuzz_data(req_map_data, extra_expected):
        async with btd6ml_test_client.put("/maps/MLXXXAB", headers=HEADERS, data=to_formdata(req_data)) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Setting Map.{path} to {sub_value} while editing a map returns {resp.status}"
            resp_data = await resp.json()
            assert "errors" in resp_data and path in resp_data["errors"], \
                f"\"{path}\" was not in response.errors"


@pytest.mark.maps
@pytest.mark.put
@pytest.mark.post
async def test_invalid_fields(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """Test adding and editing map with invalid fields in the payload"""
    await mock_auth(perms={1: Permissions.curator(), 2: Permissions.curator()})

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

    async def call_endpoints(
            req_data: dict,
            error_path: str,
            error_msg: str = "",
            test_edit: bool = True,
            test_add: bool = True,
    ):
        error_msg = error_msg.replace("[keypath]", error_path)
        if "aliases" in error_path:
            error_path += ".alias"
        if test_add:
            async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_data)) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"
        if test_edit:
            async with btd6ml_test_client.put("/maps/MLXXXEI", headers=HEADERS, data=to_formdata(req_data)) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Editing {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

    # Code fields
    validations = [
        ("AAAAAA1", "a map with an invalid code"),
        ("AAAAAAAA", "a map with an invalid code"),
        ("MLXXXEJ", "a map with an already inserted map"),
        ("AAAAAAA", "a map with a nonexistent code"),
    ]
    invalid_schema = {None: ["code"], "additional_codes": ["code"]}
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg, test_edit=edited_path != "code")

    # User fields
    validations = [
        ("999999999", "a map with a nonexistent user"),
        ("a", "a map with a non-numeric user"),
    ]
    invalid_schema = {"creators": ["id"], "verifiers": ["id"]}
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg)

    # String fields
    validations = [
        ("", f"a map with an empty [keypath]"),
        ("a"*1000, f"a map with a [keypath] too long"),
    ]
    invalid_schema = {
        None: ["name", "r6_start", "map_preview_url"],
        "additional_codes": ["description"],
        "creators": ["role"],
    }
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg)

    # Non-negative fields. -1 is a special value so that would be valid
    validations = [(-2, f"a map with a negative [keypath]")]
    invalid_schema = {None: ["placement_curver", "placement_allver", "difficulty"]}
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg)

    # Integer too large
    validations = [(999999, f"a map with a [keypath] too large")]
    invalid_schema = {None: ["difficulty"]}
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg)

    # Already taken aliases
    validations = [("ml20", f"an already taken alias")]
    invalid_schema = {"aliases": [0]}
    for req_data, edited_path, error_msg in invalidate_field(req_map_data, invalid_schema, validations):
        await call_endpoints(req_data, edited_path, error_msg)


@pytest.mark.maps
@pytest.mark.put
@pytest.mark.post
async def test_req_with_images(btd6ml_test_client, mock_auth, map_payload, valid_codes, save_image):
    """Test adding and editing map with images in the payload works"""
    async def assert_images(code: str, expected: tuple[str, str], full: bool = False):
        async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
            resp_data = await resp_get.json()
            check_url = resp_data["r6_start"] if full else resp_data["r6_start"].split("/")[-1]
            assert check_url == expected[0], "Map.r6_start differs from expected"
            check_url = resp_data["map_preview_url"] if full else resp_data["map_preview_url"].split("/")[-1]
            assert check_url == expected[1], "Map.map_preview_url differs from expected"

    await mock_auth(perms={None: Permissions.curator()})

    r6_start_path, r6_hash = save_image(1, filename="r6start.png", with_hash=True)
    preview_path, prev_hash = save_image(2, filename="preview.png", with_hash=True)

    req_map_data = {
        **map_payload(valid_codes[0]),
        "difficulty": 0,
        "creators": [{"id": "1", "role": None}],
    }
    form_data = to_formdata(req_map_data)
    form_data.add_field("r6_start", r6_start_path.open("rb"))
    form_data.add_field("map_preview_url", preview_path.open("rb"))
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=form_data) as resp:
        assert resp.ok, f"Adding a map with images in the payload return {resp.status}"
        await assert_images(valid_codes[0], (f"{r6_hash}.webp", f"{prev_hash}.webp"))

    form_data = to_formdata(req_map_data)
    form_data.add_field("r6_start", r6_start_path.open("rb"))
    form_data.add_field("map_preview_url", preview_path.open("rb"))
    async with btd6ml_test_client.put(f"/maps/{valid_codes[0]}", headers=HEADERS, data=form_data) as resp:
        assert resp.ok, f"Editing a map with images in the payload return {resp.status}"
        await assert_images(valid_codes[0], (f"{r6_hash}.webp", f"{prev_hash}.webp"))

    form_data = to_formdata({
        **req_map_data,
        "r6_start": "https://example.com/img1.png",
        "map_preview_url": "https://example.com/img2.png",
    })
    form_data.add_field("r6_start", r6_start_path.open("rb"))
    form_data.add_field("map_preview_url", preview_path.open("rb"))
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
    form_data.add_field("r6_start", r6_start_path.open("rb"))
    form_data.add_field("map_preview_url", preview_path.open("rb"))
    async with btd6ml_test_client.post(f"/maps", headers=HEADERS, data=form_data):
        assert resp.ok, f"Adding a map with images in the payload and json body return {resp.status}"
        await assert_images(
            valid_codes[1], ("https://example.com/img1.png", "https://example.com/img2.png"), full=True
        )


@pytest.mark.maps
@pytest.mark.post
@pytest.mark.put
async def test_missing_fields(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """Test a request with some missing fields"""
    await mock_auth(perms={51: Permissions.curator()})

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


@pytest.mark.maps
@pytest.mark.put
@pytest.mark.post
async def test_moderator_perms(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """
    Test Maplist Mods adding and editing Expert List attributes, and vice versa.
    """
    async def assert_map_placements(map_code: str, expected: tuple[int, int, int], mod_type: str):
        async with btd6ml_test_client.get(f"/maps/{map_code}") as resp:
            resp_map_data = await resp.json()
            assert resp_map_data["placement_curver"] == expected[0], \
                f"{mod_type} Moderator {'did not change' if mod_type == 'Maplist' else 'changed'} List Placement"
            assert resp_map_data["placement_allver"] == expected[1], \
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
    await mock_auth(perms={1: Permissions.curator(), 2: Permissions.curator()})
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
            f"POST /maps/{test_code} returned {resp.status}"

    async with btd6ml_test_client.put("/maps/MLXXXAA", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.ok, f"PUT /maps/MLXXXAA returned {resp.status}"
        await assert_map_placements("MLXXXAA", (10, 10, None), "Maplist")

    # Expert Mods
    await mock_auth(perms={51: Permissions.curator()})
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
            f"POST /maps/{test_code} returned {resp.status}"

    async with btd6ml_test_client.put("/maps/MLXXXAB", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.ok, f"PUT /maps/MLXXXAB returned {resp.status}"
        await assert_map_placements("MLXXXAB", (1, None, 2), "Experts")


@pytest.mark.delete
async def test_forbidden(btd6ml_test_client, mock_auth):
    """Test a user adding, editing or deleting maps if unauthorized"""
    async def make_admin_requests(
            test_label: str,
            expected_status: int,
    ) -> None:
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

    await mock_auth(unauthorized=True)
    await make_admin_requests("unauthorized", http.HTTPStatus.UNAUTHORIZED)

    await mock_auth()
    await make_admin_requests("missing permissions", http.HTTPStatus.FORBIDDEN)


@pytest.mark.maps
class TestEditMaps:
    @pytest.mark.put
    async def test_edit(self, btd6ml_test_client, mock_auth, map_payload, valid_codes):
        """
        Test editing a map with a correct payload works, and rearranging maps on
        the list correctly.
        """
        await mock_auth(perms={1: Permissions.curator(), 2: Permissions.curator(), 51: Permissions.curator()})

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
                "placement_allver": req_map_data["placement_allver"],
                "placement_curver": req_map_data["placement_curver"],
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
    async def test_delete(self, btd6ml_test_client, mock_auth):
        """Test deleting a map, and all other maps rearranging"""
        await mock_auth(perms={None: Permissions.curator()})

        last_map = "MLXXXEJ"
        async with btd6ml_test_client.delete(f"/maps/{last_map}", headers=HEADERS) as resp, \
                btd6ml_test_client.get(f"/maps/{last_map}") as resp_get:
            assert resp.ok, f"Delete map with correct perms returned {resp.status}"
            assert resp_get.ok, f"Get deleted map returned {resp_get.status}"
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
    async def test_delete_missing_perms(self, btd6ml_test_client, mock_auth):
        """Test deleting a map without having the perms to delete it completely"""
        code = "MLXXXDJ"
        prev_values = (40, 35, 0)

        formats = [1, 2, 51]
        for i, format_id in enumerate(formats):
            await mock_auth(perms={format_id: {Permissions.delete.map}})
            async with btd6ml_test_client.delete(f"/maps/{code}", headers=HEADERS) as resp, \
                    btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                assert resp.ok, f"Deleting a map with correct perms returned {resp.status}"
                resp_map_data = await resp_get.json()
                if i == len(formats)-1:
                    assert resp_map_data["deleted_on"] is not None, \
                        "Map.deleted_on is still None after last partial deletion"
                else:
                    assert resp_map_data["deleted_on"] is None, \
                        "Map.deleted_on is not None after partial deletion"

                assert resp_map_data["placement_curver"] is None, \
                    "Map.placement_curver is not None after deletion"
                assert resp_map_data["placement_allver"] == (None if i >= 1 else prev_values[1]), \
                    f"Map.placement_allver is {'not' if i >= 1 else ''} None after deletion"
                assert resp_map_data["difficulty"] == (None if i >= 2 else prev_values[2]), \
                    f"Map.difficulty is {'not' if i >= 2 else ''} None after deletion"

    @pytest.mark.put
    async def test_edit_legacy_map(self, btd6ml_test_client, mock_auth, map_payload):
        """Test editing a legacy map fails. It only succeeds if leaving the placements untouched"""
        async def assert_legacy_role(code, uid, placement):
            async with btd6ml_test_client.get(f"/maps/{code}") as resp_get:
                resp_map_data = await resp_get.json()
                assert resp_map_data["creators"] == [{"id": str(uid), "role": "Legacy Role", "name": f"usr{uid}"}], \
                    "Legacy map not edited correctly"
                assert resp_map_data["placement_curver"] == placement, \
                    "Legacy placement was changed"

        await mock_auth(perms={1: Permissions.curator()})

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
    async def test_reassign_aliases(self, btd6ml_test_client, mock_auth, map_payload):
        """Test adding aliases to a map reclaimed them from a deleted one"""
        await mock_auth(perms={51: Permissions.curator()})

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
async def test_large_placements(btd6ml_test_client, mock_auth, map_payload, valid_codes):
    """Test adding/editing a map with a really large placement"""
    await mock_auth(perms={None: Permissions.curator()})

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
            assert resp_map_data["placement_curver"] is None, \
                "Map.placement_curver is not None when added with a large payload"
            assert resp_map_data["placement_allver"] is None, \
                "Map.placement_allver is not None when added with a large payload"

    async with btd6ml_test_client.get(f"/maps/MLXXXAA") as resp_get:
        prev_map_data = await resp_get.json()
    async with btd6ml_test_client.put("/maps/MLXXXAA", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"Adding map with large placements returns {resp.status}"
        async with btd6ml_test_client.get(f"/maps/MLXXXAA") as resp_get:
            resp_map_data = await resp_get.json()
            assert resp_map_data["placement_curver"] == prev_map_data["placement_curver"], \
                "Map.placement_curver is not None when added with a large payload"
            assert resp_map_data["placement_allver"] == prev_map_data["placement_allver"], \
                "Map.placement_allver is not None when added with a large payload"

    await mock_auth(perms={1: Permissions.curator(), 2: Permissions.curator()})
    async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(req_map_data)) as resp:
        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
            f"Adding map with large placements as a list moderator returns {resp.status}"
