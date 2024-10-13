import pytest


@pytest.mark.get
@pytest.mark.completions
class TestCompletionList:
    """
    Test all endpoints returning only accepted, not deleted, and
    not overridden completions.
    """

    async def test_map_completions(self, btd6ml_test_client):
        """Test getting a map's completions"""
        pytest.skip("Not Implemented")

    async def test_unknown_map_completions(self, btd6ml_test_client):
        """Test getting a nonexistent map's completions"""
        pytest.skip("Not Implemented")

    async def test_map_completions_paginate(self, btd6ml_test_client):
        """Test getting a map's completions, by page"""
        pytest.skip("Not Implemented")

    async def test_user_completions(self, btd6ml_test_client):
        """Test getting a user's completions"""
        pytest.skip("Not Implemented")

    async def test_unknown_user_completions(self, btd6ml_test_client):
        """Test getting a nonexistent user's completions"""
        pytest.skip("Not Implemented")

    async def test_user_completions_paginate(self, btd6ml_test_client):
        """Test getting a user's completions, by page"""
        pytest.skip("Not Implemented")

    async def test_own_completions_on(self, btd6ml_test_client):
        """Test getting a user's own completions on a map"""
        pytest.skip("Not Implemented")

    async def test_recent_completions(self, btd6ml_test_client):
        """Test recent completions"""
        pytest.skip("Not Implemented")
