import pytest
import http
from ..testutils import fuzz_data
from ..mocks import DiscordPermRoles

HEADERS = {"Authorization": "Bearer test_token"}
START_CONFIG = {
    "points_top_map": 100,
    "points_bottom_map": 5,
    "formula_slope": 0.88,
    "points_extra_lcc": 20,
    "points_multi_gerry": 2,
    "points_multi_bb": 3,
    "decimal_digits": 0,
    "map_count": 50,
    "current_btd6_ver": 441,
    "exp_points_casual": 1,
    "exp_points_medium": 2,
    "exp_points_high": 3,
    "exp_points_true": 4,
    "exp_points_extreme": 5,
    "exp_nogerry_points_casual": 0,
    "exp_nogerry_points_medium": 0,
    "exp_nogerry_points_high": 0,
    "exp_nogerry_points_true": 0,
    "exp_nogerry_points_extreme": 0,
    "exp_bb_multi": 1,
    "exp_lcc_extra": 0,
}
MAPLIST_CONFIG = {
    "points_top_map": 10,
    "points_bottom_map": 10,
    "formula_slope": 10,
    "points_extra_lcc": 10,
    "points_multi_gerry": 10,
    "points_multi_bb": 10,
    "decimal_digits": 10,
    "map_count": 10,
    "current_btd6_ver": 10,
}
EXPLIST_CONFIG = {
    "current_btd6_ver": 30,
    "exp_points_casual": 30,
    "exp_points_medium": 30,
    "exp_points_high": 30,
    "exp_points_true": 30,
    "exp_points_extreme": 30,
    "exp_nogerry_points_casual": 1,
    "exp_nogerry_points_medium": 3,
    "exp_nogerry_points_high": 6,
    "exp_nogerry_points_true": 9,
    "exp_nogerry_points_extreme": 41,
    "exp_bb_multi": 2,
    "exp_lcc_extra": 1,
}


@pytest.mark.get
async def test_get_config(btd6ml_test_client):
    """Test getting config vars"""
    async with btd6ml_test_client.get("/config") as resp:
        assert resp.status == http.HTTPStatus.OK, f"Getting config returned {resp.status}"
        assert START_CONFIG == await resp.json(), "Returned config differs from expected"


@pytest.mark.put
async def test_edit_config(btd6ml_test_client, mock_auth, assert_state_unchanged):
    """Test successfully editing config variable"""
    async def assert_edit_success(perms: int, config: dict):
        mod_name = "Maplist" if perms & DiscordPermRoles.MAPLIST_MOD else "Expert"
        await mock_auth(perms=perms)
        req_data = {"config": {**START_CONFIG, **config}}
        async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"
            resp_data = await resp.json()
            assert "errors" in resp_data and len(resp_data["errors"]) == 0, \
                f"Errors present in response when modifying config as {mod_name} Mod"
            assert "data" in resp_data and config == resp_data["data"], \
                f"Modified config vars as {mod_name} Mod differ from expected"

    await assert_edit_success(DiscordPermRoles.MAPLIST_MOD, MAPLIST_CONFIG)
    await assert_edit_success(DiscordPermRoles.EXPLIST_MOD, EXPLIST_CONFIG)


@pytest.mark.put
class TestValidate:
    async def test_edit_config_fail(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test config variables are correctly gated by their perms"""
        async def assert_edit_fail(perms: int, config: dict):
            mod_name = "Maplist" if perms & DiscordPermRoles.MAPLIST_MOD else "Expert"
            vars_name = "Expert" if perms & DiscordPermRoles.MAPLIST_MOD else "Maplist"
            await mock_auth(perms=perms)
            req_data = {"config": config}
            async with assert_state_unchanged("/config"):
                async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and len(resp_data["errors"]) == 0, \
                        f"Errors present in response when modifying {vars_name} config vars as {mod_name} Mod"
                    assert "data" in resp_data and len(resp_data["data"]) == 0, \
                        f"Some config vars were returned as {mod_name} Mod editing {vars_name} config vars"

        explist_only = {
            key: EXPLIST_CONFIG[key]
            for key in EXPLIST_CONFIG
            if key not in MAPLIST_CONFIG
        }
        maplist_only = {
            key: MAPLIST_CONFIG[key]
            for key in MAPLIST_CONFIG
            if key not in EXPLIST_CONFIG
        }
        await assert_edit_fail(DiscordPermRoles.MAPLIST_MOD, explist_only)
        await assert_edit_fail(DiscordPermRoles.EXPLIST_MOD, maplist_only)

    async def test_extra_fields(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test adding random config var names in the payload"""
        req_data = {"config": {"nonexistent": 3}}
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        async with assert_state_unchanged("/config"):
            async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Editing config with nonexistent fields returned {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and "nonexistent" in resp_data["errors"], \
                    "Nonexistent field was not present in response errors"
                assert "data" in resp_data and len(resp_data["data"]) == 0, \
                    "Some config vars were returned while editing nonexistent config vars"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test setting fields to a different datatype, one by one"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        for req_data, path, dtype in fuzz_data({"config": START_CONFIG}, int_as_float=True):
            async with assert_state_unchanged("/config"):
                async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting {path} to {dtype} returns {resp.status}"

    async def test_unauthorized(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test editing config vars as an unauthorized user"""
        await mock_auth(unauthorized=True)
        async with assert_state_unchanged("/config"):
            async with btd6ml_test_client.put("/config") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Editing config without an Authorization header returned {resp.status}"

        async with assert_state_unchanged("/config"):
            async with btd6ml_test_client.put("/config", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Editing config with an invalid token returned {resp.status}"

        await mock_auth()
        async with assert_state_unchanged("/config"):
            async with btd6ml_test_client.put("/config", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Editing config without having perms returned {resp.status}"

