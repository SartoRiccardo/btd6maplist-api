import pytest
import http
from ..mocks import DiscordPermRoles
from ..testutils import to_formdata, formdata_field_tester, fuzz_data, invalidate_field, remove_fields
import config

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.post
@pytest.mark.submissions
async def test_submit_completion(btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image):
    """Test a valid completion submission"""
    SUBMITTER_ID = 30

    proof_urls = [
        "https://youtu.be/JDwNAlvz",
        "https://youtu.be/DcNFeVto",
    ]

    expected_completion = {
        "id": 666,
        "map": "MLXXXAA",
        "users": [
            {"id": str(SUBMITTER_ID), "name": f"usr{SUBMITTER_ID}"},
        ],
        "black_border": False,
        "no_geraldo": False,
        "current_lcc": False,
        "lcc": None,
        "format": 1,
        "subm_proof_img": [
            f"{config.MEDIA_BASE_URL}/13f1b543d32cdbfb54e04e66b3544a91da29c8dc6e6b684eaa08982b95057472.png",
        ],
        "subm_proof_vid": proof_urls,
        "accepted_by": None,
        "created_on": 0,  # Won't predict this
        "deleted_on": None,
        "subm_notes": None,
    }

    mock_discord_api(user_id=SUBMITTER_ID)
    req_submission = comp_subm_payload()
    req_submission["video_proof_url"] = proof_urls
    req_form = to_formdata(req_submission)
    req_form.add_field("proof_completion", save_image(5, filename="pc1.png").open("rb"))
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS, data=req_form) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Submitting a map with a correct payload returns {resp.status}"
        async with btd6ml_test_client.get(resp.headers['Location']) as resp_get:
            assert resp_get.status == http.HTTPStatus.OK, \
                f"Fetching newly submitted completion returns {resp_get.status}"
            completion = await resp_get.json()
            expected_completion["created_on"] = completion["created_on"]
            assert expected_completion == completion, "New submission differs from expected"


@pytest.mark.post
@pytest.mark.submissions
async def test_multi_images_urls(btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image):
    """Test a submission including multiple images and/or video urls"""
    SUBMITTER_ID = 28

    expected_completion = {
        "id": 666,
        "map": "MLXXXAA",
        "users": [{"id": str(SUBMITTER_ID), "name": f"usr{SUBMITTER_ID}"}],
        "black_border": False,
        "no_geraldo": False,
        "current_lcc": False,
        "lcc": {
            "leftover": 10,
        },
        "format": 1,
        "subm_proof_img": [
            f"{config.MEDIA_BASE_URL}/4a611bb64cbe70ed3878a6101422dd0f3c33a95dd8f892f75df4a5cd5000d884.png",
            f"{config.MEDIA_BASE_URL}/d3fc57f37b02f5f85665422822a88ccad68e2a7386b355029aa5e3dd347e4428.png",
            f"{config.MEDIA_BASE_URL}/e22de4c14b2aa64938787ad85d7738509e8ad956975ab7d3925ac0e041da39df.png",
            f"{config.MEDIA_BASE_URL}/13f1b543d32cdbfb54e04e66b3544a91da29c8dc6e6b684eaa08982b95057472.png",
        ],
        "subm_proof_vid": [
            "https://proof.com",
        ],
        "accepted_by": None,
        "created_on": 0,  # Won't predict this
        "deleted_on": None,
        "subm_notes": "Test Submission Notes",
    }

    mock_discord_api(user_id=SUBMITTER_ID)
    req_submission = {
        **comp_subm_payload(),
        "notes": "Test Submission Notes",
        "current_lcc": True,
        "leftover": 10,
        "video_proof_url": ["https://proof.com"],
    }
    req_form = to_formdata(req_submission)
    for i in range(2, 6):
        req_form.add_field("proof_completion", save_image(i, filename=f"pc{i}.png").open("rb"))
    async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS, data=req_form) as resp:
        assert resp.status == http.HTTPStatus.CREATED, \
            f"Submitting a map with a correct payload returns {resp.status}"
        async with btd6ml_test_client.get(resp.headers['Location']) as resp_get:
            assert resp_get.status == http.HTTPStatus.OK, \
                f"Fetching newly submitted completion returns {resp_get.status}"
            completion = await resp_get.json()
            expected_completion["created_on"] = completion["created_on"]
            assert expected_completion == completion, "New submission differs from expected"


@pytest.mark.post
@pytest.mark.submissions
class TestValidateCompletion:
    @pytest.mark.users
    async def test_new_user(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image):
        """Test submitting as a new user"""
        SUBMITTING_UID = 2000000
        mock_discord_api(user_id=SUBMITTING_UID, username="test_comp_submitter")

        req_form = to_formdata(comp_subm_payload())
        req_form.add_field("proof_completion", save_image(1).open("rb"))
        async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS, data=req_form) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Submitting a completion as a new user returns {resp.status}"
            async with btd6ml_test_client.get(resp.headers["Location"]) as resp_comp:
                assert resp_comp.status == http.HTTPStatus.OK, \
                    f"Getting submission by new user returns {resp_comp.status}"
            async with btd6ml_test_client.get(f"/users/{SUBMITTING_UID}") as resp_usr:
                assert resp_usr.status == http.HTTPStatus.OK, \
                    f"Getting new user's data returns {resp.status}"
                user_data = await resp_usr.json()
                assert user_data["id"] == str(SUBMITTING_UID), "User ID differs from submitter's"
                assert user_data["name"] == "test_comp_submitter", "Username differs from submitter's"

    async def test_required_proof(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test submitting a map without the required optional fields"""
        mock_discord_api()

        proof_file = save_image(5, filename="pc1.png")

        async with assert_state_unchanged("/completions/unapproved"):
            req_submission = {
                **comp_subm_payload(),
                "black_border": True,
            }
            req_form = to_formdata(req_submission)
            req_form.add_field("proof_completion", proof_file.open("rb"))
            async with btd6ml_test_client.post(
                    "/maps/MLXXXAA/completions/submit",
                    headers=HEADERS,
                    data=req_form
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting a black border run without video proof returns {resp.status}"
                error_info = await resp.json()
                assert "errors" in error_info and "video_proof_url" in error_info["errors"], \
                    "video_proof_url is not in errors"

            req_submission = {
                **comp_subm_payload(),
                "no_geraldo": True,
            }
            req_form = to_formdata(req_submission)
            req_form.add_field("proof_completion", proof_file.open("rb"))
            async with btd6ml_test_client.post(
                    "/maps/MLXXXAA/completions/submit",
                    headers=HEADERS,
                    data=req_form
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting a no Geraldo run without video proof returns {resp.status}"
                error_info = await resp.json()
                assert "errors" in error_info and "video_proof_url" in error_info["errors"], \
                    "video_proof_url is not in errors"

            req_submission = {
                **comp_subm_payload(),
                "current_lcc": True,
            }
            req_form = to_formdata(req_submission)
            req_form.add_field("proof_completion", proof_file.open("rb"))
            async with btd6ml_test_client.post(
                    "/maps/MLXXXAA/completions/submit",
                    headers=HEADERS,
                    data=req_form
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting an LCC run without video proof returns {resp.status}"
                error_info = await resp.json()
                assert "errors" in error_info, "There is no 'errors' key in the returned payload"
                assert "video_proof_url" in error_info["errors"], \
                    "video_proof_url is not in errors"
                assert "leftover" in error_info["errors"], \
                    "leftover is not in errors"

            mock_discord_api(perms=DiscordPermRoles.NEEDS_RECORDING)
            req_submission = comp_subm_payload()
            req_form = to_formdata(req_submission)
            req_form.add_field("proof_completion", proof_file.open("rb"))
            async with btd6ml_test_client.post(
                    "/maps/MLXXXAA/completions/submit",
                    headers=HEADERS,
                    data=req_form
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting a run without video proof as a 'Needs Recording' user returns {resp.status}"
                error_info = await resp.json()
                assert "errors" in error_info and "video_proof_url" in error_info["errors"], \
                    "video_proof_url is not in errors"

    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test a submission without the required fields"""
        req_form = to_formdata(comp_subm_payload())
        req_form.add_field("proof_completion", save_image(1).open("rb"))

        for req_data, path in remove_fields(req_form):
            async with assert_state_unchanged("/completions/unapproved"):
                async with btd6ml_test_client.post(
                        "/maps/MLXXXAA/completions/submit",
                        headers=HEADERS,
                        data=req_form
                ) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Removing {path} while submitting a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api, assert_state_unchanged):
        """Test a submission from an unauthorized user, or one not in the Maplist Discord"""
        async with assert_state_unchanged("/completions/unapproved"):
            mock_discord_api(unauthorized=True)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with no Authorization header returns {resp.status}"
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with an invalid token returns {resp.status}"

            mock_discord_api(in_maplist=False)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with an invalid token returns {resp.status}"

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image,
                        assert_state_unchanged):
        """Sets all properties to every possible value, one by one"""
        subm_img = save_image(2)
        full_comp_data = {
            **comp_subm_payload(),
            "current_lcc": True,
            "video_proof_url": ["https://example.com"],
        }
        extra_expected = {
            "leftover": [float],
            "notes": [str],
        }

        mock_discord_api()
        for req_data, path, sub_value in fuzz_data(full_comp_data, extra_expected):
            async with assert_state_unchanged("/completions/unapproved"):
                req_form = to_formdata(req_data)
                req_form.add_field("proof_completion", subm_img.open("rb"))
                async with btd6ml_test_client.post(
                        "/maps/MLXXXAA/completions/submit",
                        headers=HEADERS,
                        data=req_form
                ) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                        f"Setting {path} to {sub_value} while submitting a completion returns {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and path in resp_data["errors"], \
                        f"\"{path}\" was not in response.errors"

    async def test_forbidden(self, assert_state_unchanged, mock_discord_api, btd6ml_test_client):
        """Test a submission from a user banned from submitting"""
        async with assert_state_unchanged("/completions/unapproved"):
            mock_discord_api(perms=DiscordPermRoles.BANNED)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with no Authorization header returns {resp.status}"

    async def test_submit_invalid(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test setting fields to invalid values"""
        mock_discord_api()
        proof_img = save_image(2)
        req_submission_data = {
            **comp_subm_payload(),
            "current_lcc": True,
            "leftover": 3,
            "video_proof_url": ["https://proof.com"],
        }

        async def call_endpoints(req_data: dict, error_path: str, error_msg: str = ""):
            error_msg = error_msg.replace("[keypath]", error_path)
            req_form = to_formdata(req_data)
            req_form.add_field("proof_completion", proof_img.open("rb"))
            async with assert_state_unchanged("/completions/unapproved"):
                async with btd6ml_test_client.post(
                        "/maps/MLXXXAA/completions/submit",
                        headers=HEADERS,
                        data=req_form
                ) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned %d" % resp.status
                    resp_data = await resp.json()
                    assert "errors" in resp_data and error_path in resp_data["errors"], \
                        f"\"{error_path}\" was not in response.errors"

        # String fields
        validations = [
            ("", f"a map with an empty [keypath]"),
            ("a" * 1000, f"a map with a [keypath] too long"),
        ]
        invalid_schema = {None: ["notes"]}
        for req_data, edited_path, error_msg in invalidate_field(req_submission_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

        # Non-negative fields
        validations = [(-2, f"a map with a negative [keypath]")]
        invalid_schema = {None: ["format", "leftover"]}
        for req_data, edited_path, error_msg in invalidate_field(req_submission_data, invalid_schema, validations):
            await call_endpoints(req_data, edited_path, error_msg)

    async def test_submit_invalid_formats(self, btd6ml_test_client, mock_discord_api, comp_subm_payload, save_image,
                                          assert_state_unchanged):
        """Test submitting to a deleted or pushed off the list map, or to an expert map"""
        mock_discord_api()
        proof_img = save_image(2)
        req_submission_data = comp_subm_payload()
        req_submission_data["format"] = 3
        pytest.skip("Not Implemented")


@pytest.mark.submissions
class TestHandleSubmissions:
    @pytest.mark.put
    async def test_accept_submission(self, btd6ml_test_client, mock_discord_api):
        """Test accepting a submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_edit_submission(self, btd6ml_test_client, mock_discord_api):
        """Test accepting and editing a submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_edit_invalid_fields(self, btd6ml_test_client, mock_discord_api):
        """
        Test accepting and editing a submission, while editing some fields so they become invalid
        """
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_edit_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """
        Test accepting and editing a submission, with some fields being missing
        """
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_own(self, btd6ml_test_client, mock_discord_api):
        """Test accepting one's own completion"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client, mock_discord_api):
        """Test rejecting a completion submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_reject_accept_forbidden(self, btd6ml_test_client, mock_discord_api):
        """
        Test rejecting or accepting a completion submission without having the perms to do so.
        List mods shouldn't reject a map submitted to the expert list, and vice versa.
        """
        pytest.skip("Not Implemented")
