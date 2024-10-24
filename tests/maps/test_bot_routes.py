import http
import aiohttp
import pytest
import pytest_asyncio
import json
from ..testutils import fuzz_data

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.fixture
def submission_payload():
    def generate(code: str):
        return {
            "submitter": {
                "id": "20",
                "username": "usr20",
                "avatar_url": "https://image.com/1.png",
            },
            "code": code,
            "notes": "Some Notes",
            "type": "list",
            "proposed": 0,
        }
    return generate


@pytest_asyncio.fixture
async def assert_submit_map(btd6ml_test_client, mock_discord_api, valid_codes, save_image,
                            submission_payload, submission_formdata):
    """Submits a map and checks if it's there"""
    async def submit(code_idx: int):
        mock_discord_api()
        data_str = json.dumps(submission_payload(valid_codes[code_idx]))
        proof_comp = save_image(2)
        req_data = submission_formdata(data_str, [("proof_completion", proof_comp)])

        async with btd6ml_test_client.post("/maps/submit/bot", data=req_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting a map through a bot returns {resp.status}"
            async with btd6ml_test_client.get("/maps/submit") as resp_get:
                resp_data = await resp_get.json()
                assert resp_data["submissions"][0]["code"] == valid_codes[code_idx], \
                    "Most recently submitted code differs from expected"
    return submit


@pytest.mark.bot
@pytest.mark.submissions
class TestSubmit:
    CODE_IDX = 2

    @pytest.mark.post
    async def test_submit_map(self, assert_submit_map):
        """Test submitting a map"""
        await assert_submit_map(self.CODE_IDX)

    @pytest.mark.post
    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, valid_codes, save_image,
                        submission_payload, submission_formdata):
        """Replaces every field with another datatype, one by one"""
        mock_discord_api()
        CODE = valid_codes[3]
        proof_comp = save_image(2)
        req_map_data = submission_payload(CODE)
        extra_expected = {"notes": [None]}

        for req_data, path, sub_value in fuzz_data(req_map_data, extra_expected):
            if "submitter" in path:
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
                                    finish_sign, submission_payload, mock_discord_api):
        """Test submitting a map with an invalid or missing signature"""
        mock_discord_api()
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
    async def test_reject_submission(self, btd6ml_test_client, mock_discord_api, bot_user_payload, sign_message,
                                     valid_codes):
        """Test rejecting a map submission"""
        mock_discord_api()
        req_data = bot_user_payload(20)
        signature = sign_message(valid_codes[self.CODE_IDX] + json.dumps(req_data))
        req_data = {
            "data": json.dumps(req_data),
            "signature": signature,
        }
        async with btd6ml_test_client.delete(f"/maps/submit/{valid_codes[self.CODE_IDX]}/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Deleting a map with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get("/maps/submit") as resp_get:
                resp_data = await resp_get.json()
                assert resp_data["submissions"][0]["code"] != valid_codes[self.CODE_IDX], \
                    "Deleted map is still the most recently submitted"

    @pytest.mark.delete
    async def test_reject_signature(self, mock_discord_api, btd6ml_test_client, bot_user_payload, sign_message,
                                    valid_codes):
        """Test rejecting a map submission with an invalid or missing signature"""
        mock_discord_api()
        req_data = bot_user_payload(20)
        req_data = {"data": json.dumps(req_data)}
        async with btd6ml_test_client.delete(f"/maps/submit/{valid_codes[self.CODE_IDX]}/bot", json=req_data) as resp:
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
        async with btd6ml_test_client.delete(f"/maps/submit/{valid_codes[self.CODE_IDX]}/bot", json=req_data) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting a map with an invalid signature returns {resp.status}"

    @pytest.mark.post
    @pytest.mark.delete
    async def test_resubmit_rejected_map(self, assert_submit_map):
        """Test resubmitting a map that was previously rejected"""
        await assert_submit_map(self.CODE_IDX)
