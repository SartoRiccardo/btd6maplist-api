import http
import pytest
import json
import config
import aiohttp
from ..testutils import fuzz_data, invalidate_field
from ..mocks import Permissions


@pytest.fixture
def comp_subm_payload():
    def generate(user_id: int):
        return {
            "user": {
                "id": str(user_id),
                "username": f"usr{user_id}",
                "avatar_url": "https://image.com",
            },
            "format": 1,
            "notes": None,
            "black_border": False,
            "no_geraldo": False,
            "current_lcc": False,
            "leftover": None,
            "video_proof_url": [],
        }
    return generate


@pytest.mark.bot
class TestHandleSubmissions:
    @pytest.mark.delete
    async def test_reject_signature(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test rejecting a submission with an invalid or missing signature"""
        RUN_ID = 16
        USER_ID = 40
        await mock_auth(user_id=USER_ID, perms={None: Permissions.mod()})
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)

        payload = {"data": data_str}
        async with btd6ml_test_client.delete(f"/completions/{RUN_ID}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Accepting a completion without a signature returns {resp.status}"

        signature = sign_message(f"{RUN_ID}{data_str}".encode())
        data["other"] = "appeared"
        payload = {"data": json.dumps(data), "signature": signature}
        async with btd6ml_test_client.delete(f"/completions/{RUN_ID}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Accepting a completion with an invalid signature returns {resp.status}"

    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test rejecting a submission"""
        RUN_ID = 16
        USER_ID = 40
        await mock_auth(user_id=USER_ID, perms={1: {Permissions.delete.completion}})
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)
        signature = sign_message(f"{RUN_ID}{data_str}".encode())

        async with btd6ml_test_client.get(f"/completions/{RUN_ID}") as resp_get:
            completion_data = await resp_get.json()
            del completion_data["deleted_on"]

        payload = {"data": data_str, "signature": signature}
        async with btd6ml_test_client.delete(f"/completions/{RUN_ID}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Successfully deleting a completion returns {resp.status}"

        async with btd6ml_test_client.get(f"/completions/{RUN_ID}") as resp:
            assert resp.status == http.HTTPStatus.OK, \
                f"Getting a rejected (deleted) completion returns {resp.status}"
            completion_data_now = await resp.json()
            del completion_data_now["deleted_on"]
            assert completion_data == completion_data_now

    @pytest.mark.delete
    async def test_reject_already_accepted(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test rejecting a submission"""
        RUN_ID = 15
        USER_ID = 40
        await mock_auth(user_id=USER_ID, perms={51: {Permissions.delete.completion}})
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)
        signature = sign_message(f"{RUN_ID}{data_str}".encode())

        payload = {"data": data_str, "signature": signature}
        async with btd6ml_test_client.delete(f"/completions/{RUN_ID}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Rejecting an already accepted completion returns {resp.status}"

    @pytest.mark.put
    async def test_accept_signature(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test accepting a submission with an invalid or missing signature"""
        RUN_ID = 11
        await mock_auth()
        data = bot_user_payload(40)
        data_str = json.dumps(data)

        payload = {"data": data_str}
        async with btd6ml_test_client.put(f"/completions/{RUN_ID}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Accepting a completion without a signature returns {resp.status}"

        signature = sign_message(f"{RUN_ID}{data_str}".encode())
        data["other"] = "appeared"
        payload = {"data": json.dumps(data), "signature": signature}
        async with btd6ml_test_client.put(f"/completions/{RUN_ID}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Accepting a completion with an invalid signature returns {resp.status}"

    @pytest.mark.put
    async def test_accept_submission(self, btd6ml_test_client, mock_auth, bot_user_payload,
                                     sign_message, assert_state_unchanged):
        """Test accepting a submission, more than once"""
        RUN_ID = 11
        USER_ID = 40
        await mock_auth(user_id=USER_ID, perms={51: {Permissions.edit.completion}})
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)
        signature = sign_message(f"{RUN_ID}{data_str}".encode())

        async with btd6ml_test_client.get(f"/completions/{RUN_ID}") as resp:
            old_completion = await resp.json()
            old_completion["accepted_by"] = str(USER_ID)

        payload = {"data": data_str, "signature": signature}
        async with btd6ml_test_client.put(f"/completions/{RUN_ID}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Successfully accepting a completion returns {resp.status}"

        async with assert_state_unchanged(f"/completions/{RUN_ID}") as new_completion:
            old_completion["created_on"] = new_completion["created_on"]
            assert old_completion == new_completion, \
                "Completions mismatch after being accepted"

            async with btd6ml_test_client.put(f"/completions/{RUN_ID}/accept/bot", json=payload) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Accepting a completion more than once returns {resp.status}"

    @pytest.mark.put
    async def test_accept_perms(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test accepting a completion without the proper authorization"""
        USER_ID = 40
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)

        run_id = 89
        signature = sign_message(f"{run_id}{data_str}".encode())
        payload = {"data": data_str, "signature": signature}

        await mock_auth(user_id=USER_ID, perms={51: {Permissions.edit.completion}})
        async with btd6ml_test_client.put(f"/completions/{run_id}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Accepting a completion without having edit:completion in that format returns {resp.status}"

        await mock_auth(user_id=USER_ID, perms={1: {Permissions.edit.completion}})
        async with btd6ml_test_client.put(f"/completions/{run_id}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Accepting a completion while having edit:completion in that format returns {resp.status}"

        run_id = 104
        signature = sign_message(f"{run_id}{data_str}".encode())
        payload = {"data": data_str, "signature": signature}

        await mock_auth(user_id=USER_ID, perms={None: {Permissions.edit.completion}})
        async with btd6ml_test_client.put(f"/completions/{run_id}/accept/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Accepting a completion while having edit:completion in all formats returns {resp.status}"

    @pytest.mark.put
    async def test_reject_perms(self, btd6ml_test_client, mock_auth, bot_user_payload, sign_message):
        """Test rejecting a completion without the proper authorization"""
        USER_ID = 40
        data = bot_user_payload(USER_ID)
        data_str = json.dumps(data)

        run_id = 153
        signature = sign_message(f"{run_id}{data_str}".encode())
        payload = {"data": data_str, "signature": signature}

        await mock_auth(user_id=USER_ID, perms={51: {Permissions.delete.completion}})
        async with btd6ml_test_client.delete(f"/completions/{run_id}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Rejecting a completion without having edit:completion in that format returns {resp.status}"

        await mock_auth(user_id=USER_ID, perms={1: {Permissions.delete.completion}})
        async with btd6ml_test_client.delete(f"/completions/{run_id}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Rejecting a completion while having edit:completion in that format returns {resp.status}"

        run_id = 137
        signature = sign_message(f"{run_id}{data_str}".encode())
        payload = {"data": data_str, "signature": signature}

        await mock_auth(user_id=USER_ID, perms={None: {Permissions.delete.completion}})
        async with btd6ml_test_client.delete(f"/completions/{run_id}/bot", json=payload) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Rejecting a completion while having edit:completion in all formats returns {resp.status}"


@pytest.mark.bot
@pytest.mark.post
class TestSubmission:
    MAP_CODE = "MLXXXCC"
    SUBMITTER_ID = 30

    async def test_submit_completion(self, btd6ml_test_client, mock_auth, comp_subm_payload,
                                     save_image, submission_formdata):
        """Test submitting a completion"""
        req_subm_data = comp_subm_payload(self.SUBMITTER_ID)
        await mock_auth()
        image_info = [save_image(i, f"img{i}.png", with_hash=True) for i in range(2)]
        images = [(f"proof_completion[{i}]", image_info[i][0]) for i in range(2)]
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=self.MAP_CODE)

        expected = {
            "id": 0,  # Set later
            "map": self.MAP_CODE,
            "users": [
                {"id": str(self.SUBMITTER_ID), "name": f"usr{self.SUBMITTER_ID}"},
            ],
            "black_border": False,
            "no_geraldo": False,
            "current_lcc": False,
            "lcc": None,
            "format": 1,
            "subm_proof_img": [
                f"{config.MEDIA_BASE_URL}/{image_info[0][1]}.webp",
                f"{config.MEDIA_BASE_URL}/{image_info[1][1]}.webp",
            ],
            "subm_proof_vid": [],
            "accepted_by": None,
            "created_on": 0,  # Won't predict this
            "deleted_on": None,
            "subm_notes": None,
        }

        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting a completion with a correct payload returns {resp.status}"
            async with btd6ml_test_client.get(resp.headers["Location"]) as resp_get:
                resp_data = await resp_get.json()
                expected["id"] = int(resp.headers["Location"].split("/")[-1])
                expected["created_on"] = resp_data["created_on"]
                assert resp_data == expected, "Submitted completion differs from expected"

    async def test_closed_submissions(self, btd6ml_test_client, mock_auth, comp_subm_payload,
                                      save_image, submission_formdata):
        """Test submitting a completion to a format that doesn't accept them"""
        await mock_auth()
        req_subm_data = comp_subm_payload(self.SUBMITTER_ID)
        req_subm_data["format"] = 2
        image_info = [save_image(i, f"img{i}.png", with_hash=True) for i in range(2)]
        images = [(f"proof_completion[{i}]", image_info[i][0]) for i in range(2)]
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=self.MAP_CODE)

        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Submitting a completion to a format that doesn't accept completions returns {resp.status}"
            assert "format" in (await resp.json()).get("errors", {}), \
                "\"format\" is not present in errors"

    async def test_lcc_only_submissions(self, btd6ml_test_client, mock_auth, comp_subm_payload,
                                      save_image, submission_formdata):
        """Test submitting a completion to a format that doesn't accept them"""
        MAP_CODE = "MLXXXBA"

        await mock_auth()
        req_subm_data = comp_subm_payload(self.SUBMITTER_ID)
        req_subm_data["format"] = 11
        image_info = [save_image(i, f"img{i}.png", with_hash=True) for i in range(2)]
        images = [(f"proof_completion[{i}]", image_info[i][0]) for i in range(2)]
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=MAP_CODE)

        async with btd6ml_test_client.post(f"/maps/{MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Submitting a non-LCC completion to a format that only accepts LCCs returns {resp.status}"
            assert "current_lcc" in (await resp.json()).get("errors", {}), \
                "\"current_lcc\" is not present in errors"

        req_subm_data["current_lcc"] = True
        req_subm_data["leftover"] = 999
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=MAP_CODE)
        async with btd6ml_test_client.post(f"/maps/{MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting an LCC completion to a format that only accepts LCCs returns {resp.status}"

    async def test_invalid(self, btd6ml_test_client, mock_auth, save_image, submission_formdata,
                           assert_state_unchanged, comp_subm_payload):
        """Test submitting with some invalid fields"""
        await mock_auth()
        images = [(f"proof_completion[0]", save_image(0))]
        req_subm_data = comp_subm_payload(self.SUBMITTER_ID)

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            req_form = submission_formdata(json.dumps(req_data), images, pre_sign=self.MAP_CODE)
            async with assert_state_unchanged("/completions/unapproved"), \
                    btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Submitting {error_msg} returned %d" % resp.status
                resp_data = await resp.json()
                assert "errors" in resp_data and error_path in resp_data["errors"], \
                    f"\"{error_path}\" was not in response.errors"

        # Requires proof
        validations = [
            (True, "a [keypath] completion with no video proof"),
        ]
        invalid_schema = {None: ["current_lcc", "no_geraldo", "black_border"]}
        for req_data, edited_path, error_msg in invalidate_field(req_subm_data, invalid_schema, validations):
            error_msg = error_msg.replace("[keypath]", edited_path)
            await call_endpoints(req_data, "video_proof_url", error_msg)

        req_subm_data["current_lcc"] = True
        req_subm_data["video_proof_url"] = ["https://youtu.be/iaegfi3186"]
        await call_endpoints(req_subm_data, "leftover", "an LCC completion without a leftover")

        req_subm_data["leftover"] = 3000

        # String fields
        validations = [
            ("", f"a completion with an empty [keypath]"),
            ("https://youtube.com/" + "a" * 1000, f"a completion with a [keypath] too long"),
        ]
        invalid_schema = {None: ["notes"], "video_proof_url": [0]}
        for req_data, edited_path, error_msg in invalidate_field(req_subm_data, invalid_schema, validations):
            error_msg = error_msg.replace("[keypath]", edited_path)
            await call_endpoints(req_data, edited_path, error_msg)

        # Non-negative fields
        validations = [(-2, f"a map with a negative [keypath]")]
        invalid_schema = {None: ["format", "leftover"]}
        for req_data, edited_path, error_msg in invalidate_field(req_subm_data, invalid_schema, validations):
            error_msg = error_msg.replace("[keypath]", edited_path)
            await call_endpoints(req_data, edited_path, error_msg)

        # Too much proof
        req_subm_data["video_proof_url"] = ["https://youtu.be/iaegfi3186"] * 10
        await call_endpoints(req_subm_data, "video_proof_url", "a completion with too many proof URLs")

    async def test_fuzz(self, btd6ml_test_client, mock_auth, save_image, submission_formdata,
                        comp_subm_payload):
        """Test setting every field to a different datatype, one by one"""
        SUBMITTER_ID = 30
        await mock_auth()
        images = [(f"proof_completion[0]", save_image(0))]
        req_subm_data = comp_subm_payload(SUBMITTER_ID)
        req_subm_data["video_proof_url"] = ["https://youtu.be/aefhUOEF"]
        extra_expected = {"notes": [str], "leftover": [int]}

        for req_data, path, sub_value in fuzz_data(req_subm_data, extra_expected):
            if "user" in path:
                continue
            if "leftover" in path:
                req_data["current_lcc"] = True

            req_form = submission_formdata(json.dumps(req_data), images, pre_sign=self.MAP_CODE)
            async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting {path} to {sub_value} while editing a map returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors"

    async def test_submit_signature(self, btd6ml_test_client, mock_auth, comp_subm_payload,
                                    save_image, partial_sign, finish_sign):
        """Test submitting a completion with an invalid or missing signature"""
        SUBMITTER_ID = 30
        await mock_auth()
        proof = save_image(1)

        req_subm_data = comp_subm_payload(SUBMITTER_ID)
        data_str = json.dumps(req_subm_data)

        req_form = aiohttp.FormData()
        req_form.add_field("proof_completion[0]", proof.open("rb"))
        req_form.add_field("data", json.dumps({"data": data_str}))
        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Submitting a completion from a bot without a signature returns {resp.status}"

        req_form = aiohttp.FormData()
        contents_hash = partial_sign(("MLXXXAA" + data_str).encode())
        with proof.open("rb") as fin:
            contents_hash = partial_sign(fin.read(), current=contents_hash)
        req_form.add_field("proof_completion[0]", proof.open("rb"))
        req_form.add_field("data", json.dumps({"data": data_str, "signature": finish_sign(contents_hash)}))
        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Submitting a completion from a bot with an invalid signature returns {resp.status}"

    async def test_submit_banned(self, btd6ml_test_client, mock_auth, comp_subm_payload,
                                     save_image, submission_formdata):
        """Test submitting a completion as a banned & requires recording user"""
        SUBMITTER_ID = 30
        req_subm_data = comp_subm_payload(SUBMITTER_ID)
        images = [(f"proof_completion[{i}]", save_image(i, f"img{i}.png")) for i in range(2)]
        
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=self.MAP_CODE)
        await mock_auth(user_id=SUBMITTER_ID, perms={})
        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Submitting a completion as a banned user returns {resp.status}"

        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=self.MAP_CODE)
        await mock_auth(user_id=SUBMITTER_ID, perms={None: Permissions.requires_recording()})
        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                f"Submitting a completion as a requires recording user with no video proof returns {resp.status}"

        req_subm_data["video_proof_url"].append("https://youtu.be/something")
        req_form = submission_formdata(json.dumps(req_subm_data), images, pre_sign=self.MAP_CODE)
        await mock_auth(user_id=SUBMITTER_ID, perms={None: Permissions.requires_recording()})
        async with btd6ml_test_client.post(f"/maps/{self.MAP_CODE}/completions/submit/bot", data=req_form) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting a completion as a requires recording user video proof returns {resp.status}"
