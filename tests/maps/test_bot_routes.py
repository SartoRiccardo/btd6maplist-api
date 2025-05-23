import asyncio
import http
import aiohttp
import pytest
import pytest_asyncio
import json
from ..testutils import fuzz_data, to_formdata
from ..mocks import Permissions

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.fixture
def submission_payload():
    def generate(code: str):
        return {
            "user": {
                "id": "20",
                "username": "usr20",
                "avatar_url": "https://image.com/1.png",
            },
            "code": code,
            "notes": "Some Notes",
            "format": 1,
            "proposed": 0,
        }
    return generate


@pytest_asyncio.fixture
async def assert_submit_map(btd6ml_test_client, mock_auth, valid_codes, save_image,
                            submission_payload, submission_formdata):
    """Submits a map and checks if it's there"""
    async def submit(code_idx: int):
        await mock_auth()
        data_str = json.dumps(submission_payload(valid_codes[code_idx]))
        proof_comp = save_image(2)
        req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])

        async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp, \
                btd6ml_test_client.get("/maps/submit") as resp_get:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting a map through a bot returns {resp.status}"
            resp_data = await resp_get.json()
            assert resp_data["submissions"][0]["code"] == valid_codes[code_idx], \
                "Most recently submitted code differs from expected"
    return submit


@pytest.mark.bot
@pytest.mark.submissions
@pytest.mark.post
@pytest.mark.delete
async def test_reject_discord(btd6ml_test_client, mock_auth, valid_codes, sign_message,
                              payload_format, mock_discord_api, submission_payload, bot_user_payload):
    """Test submitting and Rejecting via Discord"""
    FORMAT_ID = 2
    USER_ID = 20
    await mock_auth(user_id=USER_ID, perms={FORMAT_ID: Permissions.mod()})
    mocker = mock_discord_api(user_id=USER_ID)

    payload = payload_format()
    payload["map_submission_status"] = "open"
    async with btd6ml_test_client.put(f"/formats/{FORMAT_ID}", headers=HEADERS, json=payload) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"Editing a format with a correct payload returned {resp.status}"

    valid_data = json.dumps({
        **submission_payload(valid_codes[8]),
        "format": FORMAT_ID,
    })
    req_data = {
        "data": valid_data,
        "signature": sign_message(valid_data.encode()),
    }
    async with btd6ml_test_client.post("/maps/submit/bot", json=req_data) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Submitting a map through Discord on a format with a webhook returns {resp.status}"

    await asyncio.sleep(0.5)
    assert len(mocker.wh_events) == 1, "Webhook information wasn't sent on map submission"
    assert mocker.wh_events[0]["action"] == "post", "Wrong webhook event was sent on map submission"
    wh_msg_id = mocker.wh_events[0]["msg_id"]

    valid_data = json.dumps({
        **bot_user_payload(USER_ID),
        "message_id": str(wh_msg_id),
    })
    req_data = {
        "data": valid_data,
        "signature": sign_message(valid_data.encode()),
    }
    async with btd6ml_test_client.delete("/maps/submit/bot", json=req_data) as resp:
        assert resp.status == http.HTTPStatus.NO_CONTENT, \
            f"Rejecting a map through Discord on a format with a webhook returns {resp.status}"
    await asyncio.sleep(0.5)
    assert len(mocker.wh_events) == 2, "Webhook information wasn't sent on map submission deletion"
    assert mocker.wh_events[1] == {"action": "patch", "msg_id": wh_msg_id}, \
        "Wrong webhook event was sent on map submission deletion"


@pytest.mark.bot
@pytest.mark.submissions
class TestSubmit:
    CODE_IDX = 2

    @pytest.mark.post
    async def test_submit_map(self, assert_submit_map):
        """Test submitting a map"""
        await assert_submit_map(self.CODE_IDX)

    @pytest.mark.post
    async def test_closed_submissions(self, btd6ml_test_client, mock_auth, submission_payload, save_image,
                                      valid_codes, assert_state_unchanged, submission_formdata):
        """Test submitting a map to a format with map submissions closed"""
        await mock_auth()

        proof_completion = save_image(1)
        valid_data = submission_payload(valid_codes[4])
        valid_data["format"] = 2
        data_str = json.dumps(valid_data)
        proof_comp = save_image(2)
        req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])

        form_data = to_formdata(valid_data)
        form_data.add_field("proof_completion", proof_completion.open("rb"))
        async with assert_state_unchanged("/maps/submit"), \
                btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Submitting a map to a list with map submissions closed returned {resp.status}"

    @pytest.mark.post
    async def test_fuzz(self, btd6ml_test_client, mock_auth, valid_codes, save_image,
                        submission_payload, submission_formdata):
        """Replaces every field with another datatype, one by one"""
        await mock_auth()
        CODE = valid_codes[3]
        proof_comp = save_image(2)
        req_map_data = submission_payload(CODE)
        extra_expected = {"notes": [None]}

        for req_data, path, sub_value in fuzz_data(req_map_data, extra_expected):
            if "user" in path:
                continue

            data_str = json.dumps(req_data)
            req_form = submission_formdata(data_str, [("proof_completion", proof_comp)])
            async with btd6ml_test_client.post("/maps/submit/bot", data=req_form) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting a map through a bot with {sub_value} in {path} returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors when set to {sub_value}"

    @pytest.mark.post
    async def test_submit_signature(self, btd6ml_test_client, save_image, partial_sign,
                                    finish_sign, submission_payload, mock_auth):
        """Test submitting a map with an invalid or missing signature"""
        await mock_auth()
        CODE = "INVALID"

        data_str = json.dumps(submission_payload(CODE))
        proof_comp = save_image(2)
        contents_hash = partial_sign(data_str.encode())
        with proof_comp.open("rb") as fin:
            contents_hash = partial_sign(fin.read(), current=contents_hash)
        signature = finish_sign(contents_hash)

        req_data = aiohttp.FormData()
        req_data.add_field("proof_completion", proof_comp.open("rb"))
        req_data.add_field("data", json.dumps({"data": data_str}))
        async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Submitting a map without a signature returns {resp.status}"

        req_data = aiohttp.FormData()
        req_data.add_field("proof_completion", proof_comp.open("rb"))
        req_data.add_field("data", json.dumps({"data": data_str+"a", "signature": signature}))
        async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Submitting a map with an invalid signature returns {resp.status}"

    @pytest.mark.delete
    async def test_reject_signature(self, mock_auth, btd6ml_test_client, bot_user_payload, sign_message,
                                    valid_codes):
        """Test rejecting a map submission with an invalid or missing signature"""
        await mock_auth()
        req_data = bot_user_payload(20)
        req_data = {"data": json.dumps(req_data)}
        async with btd6ml_test_client.delete(f"/maps/submit/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Deleting a map without a signature returns {resp.status}"

        signature = sign_message(valid_codes[self.CODE_IDX] + json.dumps(req_data))
        req_data = {
            "data": json.dumps({
                **bot_user_payload(20),
                "other": "hey!",
            }),
            "signature": signature,
        }
        async with btd6ml_test_client.delete(f"/maps/submit/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting a map with an invalid signature returns {resp.status}"

    @pytest.mark.post
    @pytest.mark.delete
    async def test_resubmit_rejected_map(self, assert_submit_map):
        """Test resubmitting a map that was previously rejected"""
        await assert_submit_map(self.CODE_IDX)


@pytest.mark.bot
class TestPermissions:
    @pytest.mark.post
    async def test_cannot_submit(self, valid_codes, mock_auth, save_image, submission_formdata, btd6ml_test_client,
                                 submission_payload):
        """Test submitting a map when they're banned from submitting"""
        await mock_auth(user_id=20, perms={})
        data_str = json.dumps(submission_payload(valid_codes[6]))
        proof_comp = save_image(2)
        req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])

        async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Submitting a map through a bot as a banned user returns {resp.status}"

    @pytest.mark.post
    @pytest.mark.delete
    async def test_reject_submission_perms(self, valid_codes, mock_auth, save_image, submission_formdata,
                                           btd6ml_test_client, submission_payload, bot_user_payload, sign_message):
        """Test submitting a map when they're banned from submitting"""
        # await mock_auth(user_id=20)
        # proof_comp = save_image(2)
        # maplist_code = valid_codes[5]
        # experts_code = valid_codes[6]
        #
        # data_str = json.dumps(submission_payload(maplist_code))
        # req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])
        # async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
        #     assert resp.status == http.HTTPStatus.CREATED, \
        #         f"Submitting a map returns {resp.status}"
        #
        # data = submission_payload(experts_code)
        # data["format"] = 51
        # data_str = json.dumps(data)
        # req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])
        # async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
        #     assert resp.status == http.HTTPStatus.CREATED, \
        #         f"Submitting a map returns {resp.status}"

        user_id = 30
        req_data = {
            **bot_user_payload(user_id),
            "message_id": "1000",
        }
        signature = sign_message(json.dumps(req_data))
        req_data = {"data": json.dumps(req_data), "signature": signature}

        await mock_auth(user_id=user_id, perms={51: {Permissions.delete.map_submission}})
        async with btd6ml_test_client.delete(f"/maps/submit/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting a submission without delete:map_submission on that format returns {resp.status}"

        await mock_auth(user_id=user_id, perms={1: {Permissions.delete.map_submission}})
        async with btd6ml_test_client.delete(f"/maps/submit/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Deleting a submission with delete:map_submission on that format returns {resp.status}"

        req_data = {
            **bot_user_payload(user_id),
            "message_id": "51000",
        }
        signature = sign_message(json.dumps(req_data))
        req_data = {"data": json.dumps(req_data), "signature": signature}

        await mock_auth(user_id=user_id, perms={None: {Permissions.delete.map_submission}})
        async with btd6ml_test_client.delete(f"/maps/submit/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Deleting a submission with delete:map_submission on all formats returns {resp.status}"
