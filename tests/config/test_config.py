import pytest
import http
from ..testutils import fuzz_data
from ..mocks import Permissions

HEADERS = {"Authorization": "Bearer test_token"}
START_CONFIG = {
    "points_top_map": {
        "formats": [1, 2], "value": 100.0, "type": "float",
        "description": "Points for the #1 map",
    },
    "points_bottom_map": {
        "formats": [1, 2], "value": 5.0, "type": "float",
        "description": "Points for the last map",
    },
    "formula_slope": {
        "formats": [1, 2], "value": 0.88, "type": "float",
        "description": "Formula slope",
    },
    "points_extra_lcc": {
        "formats": [1, 2], "value": 20.0, "type": "float",
        "description": "Extra points for LCCs",
    },
    "points_multi_gerry": {
        "formats": [1, 2], "value": 2.0, "type": "float",
        "description": "No Optimal Hero point multiplier",
    },
    "points_multi_bb": {
        "formats": [1, 2], "value": 3.0, "type": "float",
        "description": "Black Border point multiplier",
    },
    "decimal_digits": {
        "formats": [1, 2], "value": 0, "type": "int",
        "description": "Decimal digits to round to",
    },
    "map_count": {
        "formats": [1, 2], "value": 50, "type": "int",
        "description": "Number of maps on the list",
    },
    "current_btd6_ver": {
        "formats": [1, 2, 51], "value": 441, "type": "int",
        "description": "Current BTD6 version",
    },
    "exp_points_casual": {
        "formats": [51], "value": 1, "type": "int",
        "description": "Casual Exp completion points",
    },
    "exp_points_medium": {
        "formats": [51], "value": 2, "type": "int",
        "description": "Medium Exp completion points",
    },
    "exp_points_high": {
        "formats": [51], "value": 3, "type": "int",
        "description": "High Exp completion points",
    },
    "exp_points_true": {
        "formats": [51], "value": 4, "type": "int",
        "description": "True Exp completion points",
    },
    "exp_points_extreme": {
        "formats": [51], "value": 5, "type": "int",
        "description": "Extreme Exp completion points",
    },
    "exp_nogerry_points_casual": {
        "formats": [51], "value": 0, "type": "int",
        "description": "Casual Exp extra",
    },
    "exp_nogerry_points_medium": {
        "formats": [51], "value": 0, "type": "int",
        "description": "Medium Exp extra",
    },
    "exp_nogerry_points_high": {
        "formats": [51], "value": 0, "type": "int",
        "description": "High Exp extra",
    },
    "exp_nogerry_points_true": {
        "formats": [51], "value": 0, "type": "int",
        "description": "True Exp extra",
    },
    "exp_nogerry_points_extreme": {
        "formats": [51], "value": 0, "type": "int",
        "description": "Extreme Exp extra",
    },
    "exp_bb_multi": {
        "formats": [51], "value": 1, "type": "int",
        "description": "Base points multiplier",
    },
    "exp_lcc_extra": {
        "formats": [51], "value": 0, "type": "int",
        "description": "Extra points",
    },
}
START_CONFIG_REQ = {key: START_CONFIG[key]["value"] for key in START_CONFIG}
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
        resp_data = await resp.json()
        for k in resp_data:
            resp_data[k]["formats"].sort()
        assert resp.status == http.HTTPStatus.OK, f"Getting config returned {resp.status}"
        assert START_CONFIG == resp_data, "Returned config differs from expected"


@pytest.mark.put
async def test_edit_config(btd6ml_test_client, mock_auth):
    """Test successfully editing config variable"""
    async def assert_edit_success(perms: dict[int, set[str]], config: dict):
        await mock_auth(perms=perms)
        req_data = {"config": {**START_CONFIG_REQ, **config}}
        async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"
            resp_data = await resp.json()
            assert "errors" in resp_data and len(resp_data["errors"]) == 0, \
                f"Errors present in response when modifying config with a correct payload"
            assert "data" in resp_data and config == resp_data["data"], \
                f"Modified config vars with perms {perms} differ from expected"

    await assert_edit_success({1: {Permissions.edit.config}}, MAPLIST_CONFIG)
    await assert_edit_success({51: {Permissions.edit.config}}, EXPLIST_CONFIG)


@pytest.mark.put
class TestValidate:
    async def test_edit_config_fail(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test config variables are correctly gated by their perms"""
        async def assert_edit_fail(perms: dict[int, set[str]], config: dict):
            await mock_auth(perms=perms)
            req_data = {"config": config}
            async with assert_state_unchanged("/config"):
                async with btd6ml_test_client.put("/config", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.OK, f"Editing config returned {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and len(resp_data["errors"]) == 0, \
                        f"Errors present in response when modifying config vars with a correct payload but no perms"
                    assert "data" in resp_data and len(resp_data["data"]) == 0, \
                        f"Some config vars were returned as perms {perms}"

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
        await assert_edit_fail({1: {Permissions.edit.config}}, explist_only)
        await assert_edit_fail({51: {Permissions.edit.config}}, maplist_only)

    async def test_extra_fields(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test adding random config var names in the payload"""
        req_data = {"config": {"nonexistent": 3}}
        await mock_auth(perms={None: {Permissions.edit.config}})
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
        await mock_auth(perms={None: {Permissions.edit.config}})
        for req_data, path, dtype in fuzz_data({"config": START_CONFIG_REQ}, int_as_float=True):
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
            async with btd6ml_test_client.put("/config", headers=HEADERS, json={"config": {"exp_lcc_extra": 3}}) as resp:
                assert resp.status == http.HTTPStatus.FORBIDDEN, \
                    f"Editing config without having perms returned {resp.status}"

