import http
import math
import json
import pathlib
import pytest
import requests
from ..mocks import DiscordPermRoles
from ..testutils import to_formdata, formdata_field_tester, fuzz_data

HEADERS = {"Authorization": "Bearer test_access_token"}


def to_subm_formdata(subm_data: dict, img_url: str, tmp_path: pathlib.Path):
    form_data = to_formdata(subm_data)
    path = tmp_path / "proof_completion.png"
    path.write_bytes(requests.get(img_url).content)
    form_data.add_field("proof_completion", path.open("rb"))
    return form_data


@pytest.mark.get
@pytest.mark.submissions
class TestGetSubmissions:
    async def test_submissions(self, btd6ml_test_client):
        """Test getting the submissions, and the pagination"""
        async with btd6ml_test_client.get("/maps/submit") as resp:
            assert resp.status == http.HTTPStatus.OK, f"GET /maps/submit returned {resp.status}"
            resp_maps = await resp.json()
            expected_items = 120-9  # Implicitly makes sure there also aren't any duplicates
            expected_pages = math.ceil(expected_items/50)
            assert resp_maps["total"] == expected_items, "Total submission count differs from expected"
            assert resp_maps["pages"] == expected_pages, "Total page count differs from expected"
            for i, subm in enumerate(resp_maps["submissions"]):
                if i > 0:
                    assert subm["created_on"] >= resp_maps["submissions"][i]["created_on"], \
                        "Submission.created_on is not sorted correctly"
                assert subm["rejected_by"] is None, \
                    "Submission is rejected, expecting only pending submissions"
            for i in range(1, expected_pages+1):
                async with btd6ml_test_client.get(f"/maps/submit?page={i}") as resp_page:
                    assert resp_page.status == http.HTTPStatus.OK, f"GET /maps/submit?page={i} returned {resp.status}"
                    resp_page_data = await resp_page.json()
                    assert resp_page_data["total"] == expected_items, "Total submission count differs from expected"
                    assert resp_page_data["pages"] == expected_pages, "Total page count differs from expected"

            async with btd6ml_test_client.get(f"/maps/submit?page={expected_pages+1}") as resp_page:
                assert resp_page.status == http.HTTPStatus.OK, f"GET /maps/submit on overflown page returned {resp.status}"
                resp_page_data = await resp_page.json()
                assert resp_page_data["total"] == 0, "Total submission count on overflown page differs from expected"
                assert resp_page_data["pages"] == 0, "Total page count on overflown page differs from expected"

    async def test_all_submissions(self, btd6ml_test_client):
        """Test getting all submissions, even rejected ones"""
        async with btd6ml_test_client.get("/maps/submit?pending=all") as resp:
            assert resp.status == http.HTTPStatus.OK, f"GET /maps/submit returned {resp.status}"
            resp_maps = await resp.json()
            expected_items = 120
            expected_pages = math.ceil(expected_items/50)
            assert resp_maps["total"] == expected_items, "Total submission count differs from expected"
            assert resp_maps["pages"] == expected_pages, "Total page count differs from expected"
            assert any([subm["rejected_by"] is not None for subm in resp_maps["submissions"]]), \
                "None of the submissions are rejected"
            for i, subm in enumerate(resp_maps["submissions"]):
                if i > 0:
                    assert subm["created_on"] >= resp_maps["submissions"][i]["created_on"], \
                        "Submission.created_on is not sorted correctly"

    async def test_qstring(self, btd6ml_test_client):
        """Test using purposefully wrong values in querystrings"""
        async with btd6ml_test_client.get(f"/maps/submit?page=aaaaa?pending=wrongval") as resp:
            assert resp.status == http.HTTPStatus.OK, f"GET /maps/submit with invalid qstrings returned {resp.status}"
            resp_data = await resp.json()
            expected_items = 120-9
            expected_pages = math.ceil(expected_items/50)
            assert resp_data["total"] == expected_items, \
                "Total submission count with invalid qstrings differs from expected"
            assert resp_data["pages"] == expected_pages, "Total page count with invalid qstrings differs from expected"
            for subm in resp_data["submissions"]:
                assert subm["rejected_by"] is None, \
                    "Rejected submission with invalid pending param. Should default to pending"


@pytest.mark.post
@pytest.mark.submissions
class TestSubmitMap:
    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api, map_submission_payload, valid_codes,
                                  save_image):
        """Test a submission without the required fields"""
        mock_discord_api()

        full_data = map_submission_payload(valid_codes[0])
        proof_completion = save_image("https://dummyimage.com/400x300/00ff00/000", "proof_completion.png")
        for key in full_data:
            req_data = {**full_data}
            del req_data[key]

            form_data = to_formdata(req_data)
            form_data.add_field("proof_completion", proof_completion.open("rb"))
            async with btd6ml_test_client.post("/maps/submit", headers=HEADERS, data=form_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting map with missing field {key} returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and key in resp_data["errors"], \
                    f"MapSubmission.{key} missing is not documented"

        form_fields = [
            ("data", json.dumps(full_data), {"content_type": "application/json"}),
            ("proof_completion", proof_completion.open("rb")),
        ]
        for form_data, field in formdata_field_tester(form_fields):
            async with btd6ml_test_client.post("/maps/submit", headers=HEADERS, data=form_data) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Submitting map with missing formdata field {field} returns {resp.status}"

    async def test_fuzz(self, btd6ml_test_client, mock_discord_api, map_submission_payload, valid_codes):
        """Sets every field to another datatype, one by one"""
        mock_discord_api()

        valid_data = map_submission_payload(
            valid_codes[0],
            notes="Test Submission Notes",
        )
        extra_allowed = {"notes": [None]}

        for req_data, path, sub_value in fuzz_data(valid_data, extra_allowed):
            async with btd6ml_test_client.post("/maps/submit", headers=HEADERS, data=to_formdata(req_data)) as resp:
                assert resp.status == http.HTTPStatus.BAD_REQUEST, \
                    f"Setting Map.{path} to {sub_value} while editing a map returns {resp.status}"
                resp_data = await resp.json()
                assert "errors" in resp_data and path in resp_data["errors"], \
                    f"\"{path}\" was not in response.errors when set to {sub_value}"

    async def test_invalid_fields(self, btd6ml_test_client, mock_discord_api, map_submission_payload, valid_codes):
        """Test submitting a map with invalid fields in the payload"""
        mock_discord_api()

        valid_data = map_submission_payload(
            valid_codes[0],
            notes="Test Submission Notes",
        )

        pytest.skip("Not Implemented")

    # async def test_invalid_map(self, btd6ml_test_client, mock_discord_api):
    #     """Test a submission of a map that doesn't exist or is already in the database"""
    #     pytest.skip("Not Implemented")

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test a submission from an unauthorized user or one not in the Maplist Discord"""
        pytest.skip("Not Implemented")

    async def test_banned(self, btd6ml_test_client, mock_discord_api):
        """Test a submission from a user with a banned role"""
        pytest.skip("Not Implemented")

    @pytest.mark.users
    async def test_new_user(self, btd6ml_test_client, mock_discord_api):
        """Test submitting as a new user and adding it to the database"""
        pytest.skip("Not Implemented")


@pytest.mark.submissions
class TestHandleSubmissions:
    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client, mock_discord_api):
        """Test rejecting a map submission"""
        mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD)
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBJ", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.NO_CONTENT, \
                f"Rejecting a submission returned {resp.status}"
            async with btd6ml_test_client.get("/maps/submit") as resp_get:
                resp_data = await resp_get.json()
                assert not any([subm["code"] == "SUBXBBJ" for subm in resp_data["submissions"]]), \
                    "Rejected submission still present"
            async with btd6ml_test_client.get("/maps/submit?pending=all") as resp_get:
                resp_data = await resp_get.json()
                assert any([subm["code"] == "SUBXBBJ" for subm in resp_data["submissions"]]), \
                    "Rejected submission doesn't appear among rejected"

    @pytest.mark.delete
    async def test_reject_forbidden(self, btd6ml_test_client, mock_discord_api):
        """
        Test rejecting a map submission without having the perms to do so.
        List mods shouldn't reject a map submitted to the expert list, and vice versa.
        """
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBH") as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Deleting a map submission with no headers returns {resp.status}"

        mock_discord_api(unauthorized=True)
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBH", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Deleting a map submission with an invalid token returns {resp.status}"

        mock_discord_api(in_maplist=False)
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBH", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.UNAUTHORIZED, \
                f"Deleting a map submission while not in the maplist returns {resp.status}"

        mock_discord_api()
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBH", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting a map submission without perms returns {resp.status}"

        mock_discord_api(perms=DiscordPermRoles.MAPLIST_MOD)
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBH", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting an Expert List map submission without being an Experts Mod returns {resp.status}"

        mock_discord_api(perms=DiscordPermRoles.EXPLIST_MOD)
        async with btd6ml_test_client.delete("/maps/submit/SUBXBBF", headers=HEADERS) as resp:
            assert resp.status == http.HTTPStatus.FORBIDDEN, \
                f"Deleting a Maplist List map submission without being a Maplist Mod returns {resp.status}"

    async def test_implicit_accept(self, btd6ml_test_client, mock_discord_api, map_submission_payload, valid_codes,
                                   map_payload, tmp_path):
        """Test seeing a submission disappears after the map is added to the database."""
        mock_discord_api()

        test_code = valid_codes[0]
        req_data = map_submission_payload(test_code)
        form_data = to_subm_formdata(req_data, "https://dummyimage.com/400x300/00ff00/000", tmp_path)
        async with btd6ml_test_client.post("/maps/submit", headers=HEADERS, data=form_data) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Valid submission returned {resp.status}"
            async with btd6ml_test_client.get("/maps/submit") as resp_get:
                resp_data = await resp_get.json()
                assert resp_data["submissions"][0]["code"] == test_code, \
                    "Latest submission differs from expected"

        mock_discord_api(user_id=5, perms=DiscordPermRoles.MAPLIST_MOD)
        map_data = map_payload(test_code)
        map_data["placement_curver"] = 1
        async with btd6ml_test_client.post("/maps", headers=HEADERS, data=to_formdata(map_data)) as resp:
            assert resp.status == http.HTTPStatus.CREATED, \
                f"Adding map with correct payload returns {resp.status}"
            async with btd6ml_test_client.get("/maps/submit") as resp_get:
                resp_data = await resp_get.json()
                assert resp_data["submissions"][0]["code"] != test_code, \
                    "Latest submission is still the recently added map"
            async with btd6ml_test_client.get("/maps/submit?pending=all") as resp_get:
                resp_data = await resp_get.json()
                assert resp_data["submissions"][0]["code"] != test_code, \
                    "Latest submission is still the recently added map, when showing all submissions"
