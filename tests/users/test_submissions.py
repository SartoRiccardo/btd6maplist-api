
import pytest
from tests.testutils import to_formdata
from tests.maps.conftest import map_submission_payload

@pytest.mark.get
async def test_get_map_submissions_empty(btd6ml_test_client, mock_auth):
    """Test getting map submissions when there are none."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 200
    data = await resp.json()
    assert data["total"] == 0
    assert data["pages"] == 0
    assert data["data"] == []


@pytest.mark.get
async def test_get_map_submissions_invalid_type(btd6ml_test_client, mock_auth):
    """Test that an invalid type results in a 400 response."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions?type=invalid", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 400


@pytest.mark.get
async def test_get_map_submissions_invalid_page(btd6ml_test_client, mock_auth):
    """Test that a non-numeric page results in a 400 response."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions?page=invalid", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 400


@pytest.mark.get
async def test_get_map_submissions_zero_page(btd6ml_test_client, mock_auth):
    """Test that a page of 0 results in a 400 response."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions?page=0", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 400


@pytest.mark.get
async def test_get_map_submissions_invalid_status(btd6ml_test_client, mock_auth):
    """Test that an invalid status results in a 400 response."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions?status=invalid", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 400


@pytest.mark.get
async def test_get_completion_submissions_empty(btd6ml_test_client, mock_auth):
    """Test getting completion submissions when there are none."""
    await mock_auth(user_id=123, username="test_user")
    resp = await btd6ml_test_client.get("/users/@me/submissions?type=completion", headers={"Authorization": "Bearer test_token"})
    assert resp.status == 200
    data = await resp.json()
    assert data["total"] == 0
    assert data["pages"] == 0
    assert data["data"] == []


@pytest.mark.get
async def test_get_map_submissions_with_data(btd6ml_test_client, mock_auth, map_submission_payload, save_image):
    """Test getting map submissions with data."""
    await mock_auth(user_id=123, username="test_user")
    headers = {"Authorization": "Bearer test_token"}

    # Submit a map
    map_code = "ZMYTEST"
    proof_completion = save_image(1)
    valid_data = map_submission_payload(map_code)
    form_data = to_formdata(valid_data)
    form_data.add_field("proof_completion", proof_completion.open("rb"))
    resp = await btd6ml_test_client.post("/maps/submit", headers=headers, data=form_data)
    assert resp.status == 201

    # Get submissions
    resp = await btd6ml_test_client.get("/users/@me/submissions", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["total"] == 1
    assert data["pages"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["code"] == map_code

@pytest.mark.asyncio
async def test_get_completion_submissions_with_data(btd6ml_test_client, mock_auth, comp_subm_payload, save_image):
    """Test getting completion submissions with data."""
    await mock_auth(user_id=123, username="test_user")
    headers = {"Authorization": "Bearer test_token"}

    # Submit a completion
    map_code = "MLXXXAA"
    req_submission = comp_subm_payload()
    req_form = to_formdata(req_submission)
    req_form.add_field("proof_completion", save_image(1).open("rb"))
    resp = await btd6ml_test_client.post(f"/maps/{map_code}/completions/submit", headers=headers, data=req_form)
    assert resp.status == 201

    # Get submissions
    resp = await btd6ml_test_client.get("/users/@me/submissions?type=completion", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["total"] == 1
    assert data["pages"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["map"]["code"] == map_code
