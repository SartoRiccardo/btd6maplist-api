import http
import pytest
import src.utils.validators
from ..testutils import fuzz_data, invalidate_field
from ..mocks import DiscordPermRoles


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


async def test_submit_roles():
    """Test changing a format's roles, and not interfering with other roles"""


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

        await mock_auth(perms=DiscordPermRoles.ADMIN)
        for req_data, path, dtype in fuzz_data(data, extra_expected=extra_expected, int_as_float=True):
            async with assert_state_unchanged("/roles/achievement"), \
                    btd6ml_test_client.put("/roles/achievement", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting {path} to {dtype} returns {resp.status}"

    async def test_forbidden(self, assert_state_unchanged, mock_auth, btd6ml_test_client):
        """Test a submission from a user banned from submitting"""

    async def test_submit_invalid(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test setting fields to invalid values"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
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

        # String fields
        validations = [
            ("a" * 1000, f"a role with a [keypath] too long and non-numeric"),
        ]
        invalid_schema = {
            "roles": {
                None: ["name", "tooltip_description"],
                "linked_roles": ["guild_id", "role_id"],
            }}
        for req_data, edited_path, error_msg in invalidate_field(data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        validations = [
            ("", f"a role with an empty [keypath]"),
        ]
        invalid_schema = {"roles": ["name"]}
        for req_data, edited_path, error_msg in invalidate_field(data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        # Colors & integers
        validations = [
            (-1, f"a negative number to [keypath]"),
        ]
        invalid_schema = {"roles": ["clr_border", "clr_inner", "threshold"]}
        for req_data, edited_path, error_msg in invalidate_field(data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        validations = [
            (0x1000000, f"a negative number to [keypath]"),
        ]
        invalid_schema = {"roles": ["clr_border", "clr_inner"]}
        for req_data, edited_path, error_msg in invalidate_field(data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    async def test_unauthorized(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test a submission from an unauthorized user, or one not in the Maplist Discord"""

    async def test_missing_fields(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test a submission without the required fields"""
