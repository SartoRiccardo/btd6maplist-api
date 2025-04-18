import http
import pytest
import src.utils.validators
from ..testutils import fuzz_data, invalidate_field, remove_fields
from ..mocks import Permissions


HEADERS = {"Authorization": "Bearer test_token"}
role_schema = {
    "lb_format": int,
    "lb_type": str,
    "threshold": int,
    "for_first": bool,
    "tooltip_description": str | None,
    "name": str,
    "clr_border": int,
    "clr_inner": int,
    "linked_roles": [{"guild_id": str, "role_id": str}],
}


def sample_achievement_role(threshold: int = 1):
    return {
        "threshold": threshold,
        "for_first": threshold == 0,
        "tooltip_description": "Test Tooltip",
        "name": "Test role",
        "clr_border": 0,
        "clr_inner": 0,
        "linked_roles": [{"guild_id": str(100 + threshold), "role_id": str(100 + threshold)}],
    }


@pytest.mark.get
@pytest.mark.roles
async def test_get_ach_roles(btd6ml_test_client):
    """Test getting achievement roles"""
    async with btd6ml_test_client.get("/roles/achievement") as resp:
        assert resp.status == http.HTTPStatus.OK, f"GET /roles/achievement returned {resp.status}"
        roles = await resp.json()

    for i, role in enumerate(roles):
        assert len(src.utils.validators.check_fields(role, role_schema)) == 0, \
            f"Error while validating AchievementRole[{i}]"

    found = set()
    for role in roles:
        role_min = (role["lb_format"], role["lb_type"], role["threshold"])
        assert role_min not in found, f"Duplicate role {role_min} found"


async def test_submit_roles(btd6ml_test_client, mock_auth):
    """Test changing a format's roles, and not interfering with other roles"""
    await mock_auth(perms={1: {Permissions.edit.achievement_roles}})
    data = {
        "lb_format": 1,
        "lb_type": "points",
        "roles": [
            sample_achievement_role(0),
            sample_achievement_role(10),
            sample_achievement_role(100),
        ]
    }

    def filter_roles(roles: list[dict], unchanged: bool = True) -> list[dict]:
        return [
            {
                **role,
                "linked_roles": sorted(
                    role["linked_roles"],
                    key=lambda x: (x["guild_id"], x["role_id"])
                )
            }
            for role in roles
            if unchanged and (role["lb_format"], role["lb_type"]) != (1, "points")
               or not unchanged and (role["lb_format"], role["lb_type"]) == (1, "points")
        ]

    async with btd6ml_test_client.get("/roles/achievement") as resp_pre, \
            btd6ml_test_client.put("/roles/achievement", json=data, headers=HEADERS) as resp_edit, \
            btd6ml_test_client.get("/roles/achievement") as resp_post:
        assert resp_edit.status == http.HTTPStatus.NO_CONTENT, \
            f"Editing the achievement roles returned {resp_edit.status}"

        pre_roles = await resp_pre.json()
        post_roles = await resp_post.json()
        assert filter_roles(pre_roles) == filter_roles(post_roles), \
            "The achievement roles that shouldn't have changed, changed"

        # Order of the items is important in the check. Didn't bother sorting.
        expected_new = [
            {**role, "lb_format": 1, "lb_type": "points"}
            for role in data["roles"]
        ]
        assert expected_new == filter_roles(post_roles, False), \
            "Newly inserted roles are different from expected"


class TestAchievementRoleValidation:
    async def test_fuzz(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test setting every field to a different datatype, one by one"""
        data = {
            "lb_format": 1,
            "lb_type": "points",
            "roles": [
                sample_achievement_role(10),
                sample_achievement_role(0),
                sample_achievement_role(100),
            ]
        }
        extra_expected = {"roles": {"tooltip_description": [None]}}

        await mock_auth(perms={1: {Permissions.edit.achievement_roles}})
        for req_data, path, dtype in fuzz_data(data, extra_expected=extra_expected, int_as_float=True):
            async with assert_state_unchanged("/roles/achievement"), \
                    btd6ml_test_client.put("/roles/achievement", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting {path} to {dtype} returns {resp.status}"

    async def test_forbidden(self, assert_state_unchanged, mock_auth, btd6ml_test_client):
        """Test a submission from a user without appropriate perms"""
        data = {
            "lb_format": 1,
            "lb_type": "points",
            "roles": [
                sample_achievement_role(10),
                sample_achievement_role(0),
                sample_achievement_role(100),
            ]
        }

        await mock_auth()
        async with assert_state_unchanged("/roles/achievement"), \
                btd6ml_test_client.put("/roles/achievement", headers=HEADERS, json=data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Modifying achievement roles without necessary perms returned {resp.status}"

        await mock_auth(perms={51: {Permissions.edit.achievement_roles}})
        async with assert_state_unchanged("/roles/achievement"), \
                btd6ml_test_client.put("/roles/achievement", headers=HEADERS, json=data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Modifying achievement roles without having edit:achievement_roles in that format returns " \
                f"{resp.status}"

    async def test_submit_invalid(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test setting fields to invalid values"""
        await mock_auth(perms={1: {Permissions.edit.achievement_roles}})
        data = {
            "lb_format": 1,
            "lb_type": "points",
            "roles": [
                sample_achievement_role(10),
                sample_achievement_role(0),
                sample_achievement_role(100),
            ]
        }

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with assert_state_unchanged("/roles/achievement"), \
                    btd6ml_test_client.put("/roles/achievement", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

        checks = [
            # String fields
            {
                "validations": [
                    ("a" * 1000, f"a role with a [keypath] too long and non-numeric")
                ],
                "schema": {
                    None: ["lb_type"],
                    "roles": {
                        None: ["name", "tooltip_description"],
                        "linked_roles": ["guild_id", "role_id"],
                    }
                },
            },
            {
                "validations": [
                    ("", f"a role with an empty [keypath]"),
                ],
                "schema": {"roles": ["name"]}
            },
            # Colors & integers
            {
                "validations": [
                    (-1, f"a negative number to [keypath]")
                ],
                "schema": {"roles": ["clr_border", "clr_inner", "threshold"]},
            },
            {
                "validations": [
                    (0x1000000, f"a number too large to [keypath]")
                ],
                "schema": {None: ["lb_format"], "roles": ["clr_border", "clr_inner"]},
            },
            # Role checks
            {
                "validations": [
                    ("4208402703829", "a taken Discord role from another achievement role"),
                    ("100", "a duplicate role"),
                ],
                "schema": {"roles": {"linked_roles": ["role_id"]}}
            }
        ]

        for check in checks:
            for req_data, edited_path, error_msg in invalidate_field(data, check["schema"], check["validations"]):
                if (edited_path, error_msg) == ("roles[0].linked_roles[0].role_id", "a duplicate role"):
                    edited_path = "roles[1].linked_roles[0].role_id"
                await call_endpoints(req_data, edited_path, error_msg)

    async def test_unauthorized(self, btd6ml_test_client, assert_state_unchanged):
        """Test a submission from an unauthorized user"""
        data = {
            "lb_format": 1,
            "lb_type": "points",
            "roles": [
                sample_achievement_role(10),
                sample_achievement_role(0),
                sample_achievement_role(100),
            ]
        }

        async with assert_state_unchanged("/roles/achievement"), \
                btd6ml_test_client.put("/roles/achievement", json=data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Modifying achievement roles without authentication returned {resp.status}"

    async def test_missing_fields(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test a submission without the required fields"""
        data = {
            "lb_format": 1,
            "lb_type": "points",
            "roles": [
                sample_achievement_role(10),
                sample_achievement_role(0),
                sample_achievement_role(100),
            ]
        }

        await mock_auth(perms={1: {Permissions.edit.achievement_roles}})

        for req_data, path in remove_fields(data):
            async with assert_state_unchanged(f"/roles/achievement"), \
                    btd6ml_test_client.put(f"/roles/achievement", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Removing {path} while transferring completions returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"