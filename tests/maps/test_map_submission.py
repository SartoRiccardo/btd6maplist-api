import pytest


@pytest.mark.post
@pytest.mark.submissions
class TestSubmitMap:
    async def test_submit_map(self, btd6ml_test_client, mock_discord_api):
        """Test a valid map submission"""
        pytest.skip("Not Implemented")

    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test a submission without the required fields"""
        pytest.skip("Not Implemented")

    async def test_invalid_map(self, btd6ml_test_client, mock_discord_api):
        """Test a submission of a map that doesn't exist or is already in the database"""
        pytest.skip("Not Implemented")

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test a submission from an unauthorized user or one not in the Maplist Discord"""
        pytest.skip("Not Implemented")


@pytest.mark.delete
@pytest.mark.submissions
class TestHandleSubmissions:
    async def test_reject_submission(self, btd6ml_test_client, mock_discord_api):
        """Test rejecting a map submission"""
        pytest.skip("Not Implemented")

    async def test_reject_forbidden(self, btd6ml_test_client, mock_discord_api):
        """
        Test rejecting a map submission without having the perms to do so.
        List mods shouldn't reject a map submitted to the expert list, and vice versa.
        """
        pytest.skip("Not Implemented")
