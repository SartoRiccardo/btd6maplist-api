import pytest


@pytest.mark.completions
class TestLeaderboard:
    async def test_ml_point_leaderboard(self):
        """Test the leaderboard is correctly calculated"""
        pytest.skip("Not Implemented")

    async def test_exp_point_leaderboard(self):
        """Test the expert leaderboard is correctly calculated"""
        pytest.skip("Not Implemented")

    async def test_ml_lcc_leaderboard(self):
        """Test the maplist lcc leaderboard is correctly calculated"""
        pytest.skip("Not Implemented")

    async def test_exp_lcc_leaderboard(self):
        """Test the expert lcc leaderboard is correctly calculated"""
        pytest.skip("Not Implemented")

    async def test_config_recalc(self):
        """Test the point leaderboards are updated on config var changes"""
        pytest.skip("Not Implemented")

    async def test_placement_change_recalc(self):
        """Test the maplist point leaderboard is updated on placement changes"""
        pytest.skip("Not Implemented")

    async def test_completion_change_recalc(self):
        """Test the point & lcc leaderboards are updated on placement changes"""
        pytest.skip("Not Implemented")
