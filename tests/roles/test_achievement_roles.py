import http
import pytest
import src.utils.validators


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


@pytest.mark.get
@pytest.mark.roles
async def test_get_ach_roles(btd6ml_test_client):
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
