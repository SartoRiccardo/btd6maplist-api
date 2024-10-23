import pytest


@pytest.mark.bot
class TestHandleSubmissions:
    @pytest.mark.delete
    async def test_reject_submission(self, btd6ml_test_client):
        """Test rejecting a map submission"""
        pytest.skip("Not Implemented")

    @pytest.mark.delete
    async def test_reject_signature(self, btd6ml_test_client):
        """Test rejecting a map submission with an invalid or missing signature"""
        pytest.skip("Not Implemented")


@pytest.mark.bot
@pytest.mark.post
class TestSubmit:
    async def test_submit_map(self, btd6ml_test_client):
        """Test submitting a map"""
        pytest.skip("Not Implemented")

    async def test_submit_signature(self, btd6ml_test_client):
        """Test submitting a map with an invalid or missing signature"""
        pytest.skip("Not Implemented")
