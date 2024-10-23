import pytest


@pytest.mark.bot
class TestHandleSubmissions:
    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client):
        """Test rejecting a submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_reject_signature(self, btd6ml_test_client):
        """Test rejecting a submission with an invalid or missing signature"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_submission(self, btd6ml_test_client):
        """Test accepting a submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.put
    async def test_accept_signature(self, btd6ml_test_client):
        """Test accepting a submission with an invalid or missing signature"""
        pytest.skip("Not Implemented")


@pytest.mark.bot
@pytest.mark.post
class TestSubmission:
    async def test_submit_completion(self, btd6ml_test_client):
        """Test submitting a completion"""
        pytest.skip("Not Implemented")

    async def test_submit_signature(self, btd6ml_test_client):
        """Test submitting a completion with an invalid or missing signature"""
        pytest.skip("Not Implemented")
