import pytest


@pytest.mark.post
@pytest.mark.submissions
class TestSubmitCompletion:
    async def test_submit_completion(self, btd6ml_test_client, mock_discord_api):
        """Test a valid completion submission"""
        pytest.skip("Not Implemented")

    async def test_missing_fields(self, btd6ml_test_client, mock_discord_api):
        """Test a submission without the required fields"""
        pytest.skip("Not Implemented")

    async def test_multi_images_urls(self, btd6ml_test_client, mock_discord_api):
        """Test a submission including multiple images and/or video urls"""
        pytest.skip("Not Implemented")

    async def test_multi_proof_url(self, btd6ml_test_client, mock_discord_api):
        """Test a submission which requires video proof, including the "requires proof" role"""
        pytest.skip("Not Implemented")

    async def test_unauthorized(self, btd6ml_test_client, mock_discord_api):
        """
        Test a submission from an unauthorized user, or one not in the Maplist Discord, or a banned one
        """
        pytest.skip("Not Implemented")

    @pytest.mark.users
    async def test_new_user(self, btd6ml_test_client, mock_discord_api):
        """Test submitting as a new user"""
        pytest.skip("Not Implemented")

    @pytest.mark.users
    async def test_submit_invalid_map(self, btd6ml_test_client, mock_discord_api):
        """Test submitting to a deleted or pushed off the list map"""
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
