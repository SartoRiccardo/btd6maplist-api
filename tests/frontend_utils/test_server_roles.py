import http
import pytest
from ..mocks import MemberMock, GuildMock, RoleMock, Permissions

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.get
class TestGetServerRoles:
    async def test_unauthorized(self, btd6ml_test_client, mock_auth):
        """Test getting the roles without authentication"""
        async with btd6ml_test_client.get("/server-roles") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Getting /server-roles without a token returns {resp.status}"

        await mock_auth(unauthorized=True)
        async with btd6ml_test_client.get("/server-roles", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Getting /server-roles without a valid token returns {resp.status}"

        await mock_auth()
        async with btd6ml_test_client.get("/server-roles", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Getting /server-roles without necessary permissions returns {resp.status}"

    async def test_get_valid_roles(self, btd6ml_test_client, mock_auth):
        """Test getting the selectable guilds and roles"""
        P_MANAGE_ROLES = 1 << 28
        P_ADMIN = 1 << 3

        roles = [RoleMock(i, f"Role{i}", i) for i in range(15)]
        bot_guilds = [
            GuildMock(1, "G1", roles=roles, member=MemberMock(roles=roles[8:10])),
            GuildMock(2, "G2", roles=roles, member=MemberMock(roles=roles[8:10])),
            GuildMock(3, "G3", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
            GuildMock(4, "G4", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN),
            GuildMock(5, "G5", roles=roles, member=MemberMock(roles=roles[13:]), permissions=P_ADMIN | P_MANAGE_ROLES),
            GuildMock(7, "G7", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
        ]
        user_guilds = [
            GuildMock(1, "G1", roles=roles, member=MemberMock(roles=roles[8:10])),
            GuildMock(2, "G2", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN),
            GuildMock(3, "G3", roles=roles, member=MemberMock(roles=roles[8:10])),
            GuildMock(4, "G4", roles=roles, member=MemberMock(roles=roles[13:]), permissions=P_MANAGE_ROLES),
            GuildMock(5, "G5", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN | P_MANAGE_ROLES),
            GuildMock(6, "G6", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
        ]
        expected = {
            4: [r.id for r in roles[:9]],
            5: [r.id for r in roles[:-1]],
        }

        await mock_auth(
            perms={1: Permissions.mod()},
            bot_guilds=bot_guilds,
            user_guilds=user_guilds
        )
        async with btd6ml_test_client.get("/server-roles", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting /server-roles with a valid token returns {resp.status}"
            result = await resp.json()

        assert len(expected) == len(result), "Number of returned guilds differs from expected"
