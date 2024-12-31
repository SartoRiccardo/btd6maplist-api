import pytest
import http
from ..mocks import DiscordPermRoles
from ..testutils import to_formdata, fuzz_data, invalidate_field, remove_fields
from .CompletionTest import CompletionTest
import config

HEADERS = {"Authorization": "Bearer test_token"}


@pytest.mark.post
@pytest.mark.submissions
async def test_submit_completion(btd6ml_test_client, mock_auth, comp_subm_payload, save_image):
    """Test a valid completion submission"""
    SUBMITTER_ID = 30

    proof_urls = [
        "https://youtu.be/JDwNAlvz",
        "https://youtu.be/DcNFeVto",
    ]

    expected_completion = {
        "id": 0,  # Set later
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

    await mock_auth(user_id=SUBMITTER_ID)
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
            expected_completion["id"] = completion["id"]
            expected_completion["created_on"] = completion["created_on"]
            assert expected_completion == completion, "New submission differs from expected"


@pytest.mark.post
@pytest.mark.submissions
async def test_multi_images_urls(btd6ml_test_client, mock_auth, comp_subm_payload, save_image):
    """Test a submission including multiple images and/or video urls"""
    SUBMITTER_ID = 28

    expected_completion = {
        "id": 0,  # Set later
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

    await mock_auth(user_id=SUBMITTER_ID)
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
            expected_completion["id"] = completion["id"]
            expected_completion["created_on"] = completion["created_on"]
            assert expected_completion == completion, "New submission differs from expected"


@pytest.mark.post
@pytest.mark.submissions
class TestValidateCompletion:
    @pytest.mark.users
    async def test_new_user(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image):
        """Test submitting as a new user"""
        SUBMITTING_UID = 2000000
        await mock_auth(user_id=SUBMITTING_UID, username="test_comp_submitter")

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

    async def test_required_proof(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test submitting a map without the required optional fields"""
        await mock_auth()

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

            await mock_auth(perms=DiscordPermRoles.NEEDS_RECORDING)
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

    async def test_missing_fields(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
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

    async def test_unauthorized(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test a submission from an unauthorized user, or one not in the Maplist Discord"""
        async with assert_state_unchanged("/completions/unapproved"):
            await mock_auth(unauthorized=True)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with no Authorization header returns {resp.status}"
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit", headers=HEADERS) as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with an invalid token returns {resp.status}"

    async def test_fuzz(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
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

        await mock_auth()
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

    async def test_forbidden(self, assert_state_unchanged, mock_auth, btd6ml_test_client):
        """Test a submission from a user banned from submitting"""
        async with assert_state_unchanged("/completions/unapproved"):
            await mock_auth(perms=DiscordPermRoles.BANNED)
            async with btd6ml_test_client.post("/maps/MLXXXAA/completions/submit") as resp:
                assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                    f"Submitting a completion with no Authorization header returns {resp.status}"

    async def test_submit_invalid(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
                                  assert_state_unchanged):
        """Test setting fields to invalid values"""
        await mock_auth()
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

    async def test_submit_invalid_formats(self, btd6ml_test_client, mock_auth, comp_subm_payload, save_image,
                                          assert_state_unchanged):
        """Test submitting to a deleted or pushed off the list map, or to an expert map"""
        await mock_auth()
        proof_img = save_image(2)
        req_submission_data = comp_subm_payload()
        req_submission_data["format"] = 3

        req_form = to_formdata(req_submission_data)
        req_form.add_field("proof_completion", proof_img.open("rb"))
        async with assert_state_unchanged("/completions/unapproved"):
            async with btd6ml_test_client.post(
                    "/maps/MLXXXAA/completions/submit",
                    headers=HEADERS,
                    data=req_form,
            ) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting with an invalid format returned {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and "format" in resp_data["errors"], \
                    "\"format\" is not in errors"

        TEST_FORMATS = [
            ("ELXXXAA", (1, 2)),
            ("MLXXXAA", (2, 51)),
            # ("MLAXXAA", (1, 51)),
        ]
        for code, formats in TEST_FORMATS:
            for fmt in formats:
                req_submission_data = comp_subm_payload()
                req_submission_data["format"] = fmt

                req_form = to_formdata(req_submission_data)
                req_form.add_field("proof_completion", proof_img.open("rb"))
                async with assert_state_unchanged("/completions/unapproved"):
                    async with btd6ml_test_client.post(
                            f"/maps/{code}/completions/submit",
                            headers=HEADERS,
                            data=req_form,
                    ) as resp:
                        assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                            f"Submitting with format {fmt} on map that shouldn't accept it returned {resp.status}"
                        resp_data = await resp.json()
                        assert "errors" in resp_data and "format" in resp_data["errors"], \
                            "\"format\" is not in errors"

    async def test_submit_nogerry_proof(self, btd6ml_test_client, comp_subm_payload, assert_state_unchanged, save_image):
        """Test submitting no geraldo runs on different expert difficulties"""
        subm_img = save_image(6)
        comp_data = {
            **comp_subm_payload(),
            "format": 51,
            "no_geraldo": True,
        }

        req_form = to_formdata(comp_data)
        req_form.add_field("proof_completion", subm_img.open("rb"))
        async with assert_state_unchanged("/completions/unapproved"), \
                btd6ml_test_client.post("/maps/MLXXXEC/completions/submit", headers=HEADERS, data=req_form) as resp:
            assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting expert completion without opt hero and no proof returns {resp.status}"

        req_form = to_formdata(comp_data)
        req_form.add_field("proof_completion", subm_img.open("rb"))
        async with btd6ml_test_client.post("/maps/MLXXXEA/completions/submit", headers=HEADERS, data=req_form) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                    f"Submitting a no geraldo run on a medium expert or below with no video proof returns {resp.status}"


@pytest.mark.submissions
class TestHandleSubmissions(CompletionTest):
    @pytest.mark.post
    async def test_accept_submission(self, btd6ml_test_client, mock_auth, completion_payload,
                                     assert_state_unchanged):
        """Test accepting (and editing) a submission"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)

        expected_value = {
            "id": 16,
            "map": "MLXXXAB",
            "users": [{"id": "1", "name": "usr1"}],
            "black_border": False,
            "no_geraldo": False,
            "current_lcc": False,
            "lcc": {"leftover": 1},
            "format": 1,
            "subm_proof_img": [
                "https://dummyimage.com/150x100/ff9933/000",
                "https://dummyimage.com/900x700/663399/fff",
                "https://dummyimage.com/200x200/ff00ff/fff",
            ],
            "subm_proof_vid": [
                "https://youtu.be/lpiZWTSe",
                "https://youtu.be/BZAfQqmI",
            ],
            "accepted_by": "100000",
            "created_on": 0,  # Set later
            "deleted_on": None,
            "subm_notes": None,
        }
        req_data = completion_payload()
        async with btd6ml_test_client.put("/completions/16/accept", headers=HEADERS, json=req_data) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Trying to accept a submission returns {resp.status}"
            async with btd6ml_test_client.get("/completions/16") as resp_get:
                resp_data = await resp_get.json()
                expected_value["created_on"] = resp_data["created_on"]
                assert expected_value == resp_data

        async with assert_state_unchanged("/completions/16"):
            async with btd6ml_test_client.put("/completions/16/accept", headers=HEADERS, json=req_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Trying to accept an already accepted submission returns {resp.status}"

    @pytest.mark.post
    async def test_invalid_fields(self, btd6ml_test_client, mock_auth, completion_payload,
                                  assert_state_unchanged):
        """Test adding and editing a completion with invalid fields in the payload"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        req_completion_data = completion_payload()

        async def call_endpoints(
                req_data: dict,
                error_path: str,
                error_msg: str = "",
        ):
            error_msg = error_msg.replace("[keypath]", error_path)
            async with assert_state_unchanged("/completions/29"):
                async with btd6ml_test_client.put("/completions/29/accept", headers=HEADERS, json=req_data) as resp:
                    assert resp.status == http.HTTPStatus.BAD_REQUEST, f"Adding {error_msg} returned {resp.status}"
                    resp_data = await resp.json()
                    assert "errors" in resp_data and error_path in resp_data["errors"], \
                        f"\"{error_path}\" was not in response.errors"

        await self._test_invalid_fields(req_completion_data, call_endpoints)

    @pytest.mark.post
    async def test_fuzz(self, btd6ml_test_client, mock_auth, completion_payload, assert_state_unchanged):
        """Sets all properties to every possible value, one by one"""
        await self._test_fuzz(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_put="/completions/29/accept",
            endpoint_get_put="/completions/29",
        )

    @pytest.mark.post
    async def test_missing_fields(self, btd6ml_test_client, mock_auth, completion_payload,
                                  assert_state_unchanged):
        """Test accepting and editing a completion with missing fields in the payload"""
        await self._test_missing_fields(
            btd6ml_test_client,
            mock_auth,
            completion_payload,
            assert_state_unchanged,
            endpoint_put="/completions/29/accept",
            endpoint_get_put="/completions/29",
        )

    @pytest.mark.post
    async def test_forbidden(self, btd6ml_test_client, mock_auth, assert_state_unchanged):
        """Test a user accepting a completion if they don't have perms"""
        await self._test_forbidden(
            btd6ml_test_client,
            mock_auth,
            assert_state_unchanged,
            endpoint_put="/completions/29/accept",
            endpoint_get_put="/completions/29",
        )

    @pytest.mark.post
    async def test_accept_own(self, btd6ml_test_client, mock_auth, assert_state_unchanged,
                                  completion_payload):
        """Test accepting and editing one's own completion, or adding themselves to a completion"""
        await self._test_own_completion(
            btd6ml_test_client,
            mock_auth,
            assert_state_unchanged,
            completion_payload,
            endpoint_put_own="/completions/29/accept",
            endpoint_get_own="/completions/29",
            endpoint_put_other="/completions/36/accept",
            endpoint_get_other="/completions/36",
        )

    @pytest.mark.put
    async def test_scoped_edit_perms(self, btd6ml_test_client, mock_auth, assert_state_unchanged,
                                     completion_payload):
        """Test Maplist Mods accepting Expert List completions, and vice versa"""
        await self._test_scoped_edit_perms(
            mock_auth,
            assert_state_unchanged,
            btd6ml_test_client,
            completion_payload,
            DiscordPermRoles.MAPLIST_MOD,
            endpoint_put="/completions/11/accept",
            endpoint_get="/completions/11",
        )
        await self._test_scoped_edit_perms(
            mock_auth,
            assert_state_unchanged,
            btd6ml_test_client,
            completion_payload,
            DiscordPermRoles.EXPLIST_MOD,
            endpoint_put="/completions/4/accept",
            endpoint_get="/completions/4",
        )

    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client, mock_auth):
        """Test rejecting a completion submission hard deletes it"""
        await mock_auth(perms=DiscordPermRoles.ADMIN)
        async with btd6ml_test_client.delete("/completions/29", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Deleting a completion returns {resp.status}"

        async with btd6ml_test_client.get("/completions/29", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NOT_FOUND, \
                f"Getting a deleted completion submission returned {resp.status}"
            assert resp.headers["Content-Length"] == "0", "Deleted completion returned some content"
