import pytest


@pytest.mark.completions
@pytest.mark.put
class TestTransfer:
    async def test_transfer_completions(self, btd6ml_test_client, mock_discord_api):
        """Test transferring a map's completions to another"""
        pytest.skip("Not Implemented")

    async def test_transfer_deleted(self, btd6ml_test_client, mock_discord_api):
        """Test transferring a map's completions to a deleted one or from a non-deleted one"""
        pytest.skip("Not Implemented")

    async def test_transfer_not_exists(self, btd6ml_test_client, mock_discord_api):
        """
        Test transferring a map's completions to
        or from one that doesn't exist
        """
        pytest.skip("Not Implemented")

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """Test transferring without the correct perms"""
        pytest.skip("Not Implemented")
