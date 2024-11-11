import pytest
import http

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.users
async def test_read_rules(btd6ml_test_client, mock_auth):
    """Test reading the rules one or more times"""
    USER_ID = 2000000
    USERNAME = "test_new_usr"
    await mock_auth(user_id=USER_ID, username=USERNAME)

    async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
        assert resp.status == http.HTTPStatus.OK, \
            f"Authenticating as a new user returns {resp.status}"
        resp_data = await resp.json()
        assert not resp_data["has_seen_popup"], "New user has seen popup"

    async with btd6ml_test_client.put("/read-rules", headers=HEADERS) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, f"Reading the rules returns {resp.status}"

    async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
        resp_data = await resp.json()
        assert resp_data["has_seen_popup"], "New user has still not seen popup"

    async with btd6ml_test_client.put("/read-rules", headers=HEADERS) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, f"Reading the rules returns {resp.status}"

    async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
        assert resp_data == await resp.json(), "Profile changed when reading the rules twice"
