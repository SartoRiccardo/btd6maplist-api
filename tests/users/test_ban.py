import http
import pytest
from ..mocks import Permissions
from ..testutils import HEADERS


@pytest.mark.users
class TestBans:
    async def test_ban_user(self, btd6ml_test_client, mock_auth):
        """Test banning and unbanning a user successfully"""
        await mock_auth(perms={None: {Permissions.misc.ban_user}})
        async with btd6ml_test_client.post("/users/10/ban", headers=HEADERS) as resp_ban, \
                btd6ml_test_client.get("/users/10") as resp_get_banned, \
                btd6ml_test_client.post("/users/10/unban", headers=HEADERS) as resp_unban, \
                btd6ml_test_client.get("/users/10") as resp_get_unbanned:
            assert resp_ban.status == http.HTTPStatus.NO_CONTENT, \
                f"Successfully banning a user returns {resp_ban.status}"
            assert (await resp_get_banned.json())["is_banned"], \
                "User results as not banned after being banned"
            assert resp_unban.status == http.HTTPStatus.NO_CONTENT, \
                f"Successfully unbanning a user returns {resp_unban.status}"
            assert not (await resp_get_unbanned.json())["is_banned"], \
                "User results as banned after being banned"

    async def test_unauthorized(self, btd6ml_test_client, mock_auth):
        """Test banning or unbanning a user without proper authorization"""
        await mock_auth(unauthorized=True)
        async with btd6ml_test_client.post("/users/10/ban") as resp_ban, \
                btd6ml_test_client.post("/users/10/unban") as resp_unban:
            assert resp_ban.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Banning a user without providing Authorization headers returns {resp_ban.status}"
            assert resp_unban.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Unanning a user without providing Authorization headers returns {resp_unban.status}"

        async with btd6ml_test_client.post("/users/10/ban", headers=HEADERS) as resp_ban, \
                btd6ml_test_client.post("/users/10/unban", headers=HEADERS) as resp_unban:
            assert resp_ban.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Banning a user with invalid Authorization headers returns {resp_ban.status}"
            assert resp_unban.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Unanning a user with invalid Authorization headers returns {resp_unban.status}"

    async def test_forbidden(self, btd6ml_test_client, mock_auth):
        """Test banning or unbanning a user without the necessary perms"""
        await mock_auth(perms={None: Permissions.basic()})
        async with btd6ml_test_client.post("/users/10/ban", headers=HEADERS) as resp_ban, \
                btd6ml_test_client.post("/users/10/unban", headers=HEADERS) as resp_unban:
            assert resp_ban.status == http.HTTPStatus.FORBIDDEN, \
                f"Banning a user without the necessary perms returns {resp_ban.status}"
            assert resp_unban.status == http.HTTPStatus.FORBIDDEN, \
                f"Unanning a user without the necessary perms returns {resp_unban.status}"
