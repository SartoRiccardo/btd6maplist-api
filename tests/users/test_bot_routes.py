import http
import pytest
import json
import urllib

# Only used to set up data here
HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.bot
@pytest.mark.put
@pytest.mark.users
class TestBotReadRules:
    user_id = 8888

    async def test_read_rules(self, btd6ml_test_client, mock_auth, sign_message, bot_user_payload):
        """Test reding the rules"""
        await mock_auth(user_id=self.user_id)
        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert not (await resp.json())["has_seen_popup"], "New user has seen popup"

        req_data = bot_user_payload(self.user_id)
        signature = sign_message(req_data)
        req_data = {
            "data": json.dumps(req_data),
            "signature": signature,
        }
        async with btd6ml_test_client.put(f"/read-rules/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.OK, f"Reading the rules returned {resp.status}"

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            old_resp_data = await resp.json()
            assert old_resp_data["has_seen_popup"], \
                "New user has not seen popup after reading the rules"

        async with btd6ml_test_client.put(f"/read-rules/bot?signature={signature}", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.OK, f"Reading the rules returned {resp.status}"

        async with btd6ml_test_client.post("/auth", headers=HEADERS) as resp:
            assert await resp.json() == old_resp_data, "State changed when reading the rules again"

    async def test_invalid_signature(self, btd6ml_test_client, sign_message, bot_user_payload):
        """Test sending an invalid or missing signature"""
        req_data = bot_user_payload(self.user_id)
        signature = sign_message(req_data)
        req_data["newfield"] = "hi"

        req_data = {"data": json.dumps(req_data)}
        async with btd6ml_test_client.put(f"/read-rules/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Using a missing signature returned {resp.status}"

        req_data["signature"] = signature
        async with btd6ml_test_client.put(f"/read-rules/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Using an invalid signature returned {resp.status}"


@pytest.mark.bot
class TestBotProfile:
    user_id = 30
    test_oak = "oak_veryvalidoak"

    @pytest.mark.put
    async def test_edit_profile(self, btd6ml_test_client, mock_ninja_kiwi_api, sign_message, bot_user_payload):
        """Test editing a user's profile"""
        async with btd6ml_test_client.get(f"/users/{self.user_id}") as resp:
            old_resp_data = {
                **(await resp.json()),
                "avatarURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/a5d32db006cb5d8d535a14494320fc92_ProfileAvatar26.png",
                "bannerURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/aaeaf38ca1c20d6df888cae9c3c99abe_ProfileBanner43.png",
            }

        mock_ninja_kiwi_api()
        req_data = {
            **bot_user_payload(self.user_id),
            "oak": self.test_oak,
        }
        signature = sign_message(str(self.user_id) + json.dumps(req_data))
        req_data = {
            "data": json.dumps(req_data),
            "signature": signature,
        }
        async with btd6ml_test_client.put(f"/users/{self.user_id}/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Editing a user with a correct payload/signature returned {resp.status}"

        async with btd6ml_test_client.get(f"/users/{self.user_id}") as resp:
            assert await resp.json() == old_resp_data, "User data differs from expected"

    @pytest.mark.put
    async def test_invalid_signature_put(self, btd6ml_test_client, bot_user_payload, sign_message):
        """Test sending an invalid or missing signature"""
        req_data = {
            **bot_user_payload(self.user_id),
            "oak": "oak_testoakwillbevalid",
        }
        signature = sign_message(str(self.user_id) + json.dumps(req_data))
        req_data["oak"] += "a"

        req_data = {"data": json.dumps(req_data)}
        async with btd6ml_test_client.put(f"/users/{self.user_id}/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Editing a user without a signature returned {resp.status}"

        req_data["signature"] = signature
        async with btd6ml_test_client.put(f"/users/{self.user_id}/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Editing a user with an invalid signature returned {resp.status}"

    @pytest.mark.get
    async def test_get_profile(self, btd6ml_test_client, mock_ninja_kiwi_api, sign_message):
        """Test getting a user's profile, with and without loading the OAK"""
        mock_ninja_kiwi_api()

        async with btd6ml_test_client.get(f"/users/{self.user_id}") as resp:
            user_info = {
                **await resp.json(),
                "has_seen_popup": True,
                "oak": self.test_oak,
                "permissions": [{
                    "format": None,
                    "permissions": {"create:completion_submission", "create:map_submission"},
                }]
            }

        signature = sign_message(f"{self.user_id}False".encode())
        qparams = {"signature": signature, "no_load_oak": False}
        async with btd6ml_test_client.get(f"/users/{self.user_id}/bot?{urllib.parse.urlencode(qparams)}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting a user through a bot route returns {resp.status}"
            resp_data = await resp.json()
            for perm in resp_data["permissions"]:
                perm["permissions"] = set(perm["permissions"])
            assert user_info == resp_data, "User profile gotten through a bot differs from expected"

        signature = sign_message(f"{self.user_id}True".encode())
        qparams = {"signature": signature, "no_load_oak": True}
        async with btd6ml_test_client.get(f"/users/{self.user_id}/bot?{urllib.parse.urlencode(qparams)}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting a user through a bot route without loading the OAK returns {resp.status}"
            user_info = {
                **user_info,
                "avatarURL": None,
                "bannerURL": None,
            }
            resp_data = await resp.json()
            for perm in resp_data["permissions"]:
                perm["permissions"] = set(perm["permissions"])
            assert user_info == resp_data, \
                "User profile after loading its OAK gotten through a bot differs from expected"

    @pytest.mark.get
    async def test_invalid_signature_get(self, btd6ml_test_client, sign_message):
        """Test sending an invalid or missing signature"""
        qparams = {"no_load_oak": True}
        async with btd6ml_test_client.get(f"/users/{self.user_id}/bot?{urllib.parse.urlencode(qparams)}") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Getting a user through a bot route without a signature {resp.status}"

        signature = sign_message(f"{self.user_id}false".encode())
        qparams["signature"] = signature
        async with btd6ml_test_client.get(f"/users/{self.user_id}/bot?{urllib.parse.urlencode(qparams)}") as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Getting a user through a bot route without a valid signature {resp.status}"
