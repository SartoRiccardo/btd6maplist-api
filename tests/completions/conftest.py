import pytest


@pytest.fixture
def completion_payload():
    def make():
        return {
            "user_ids": ["1"],
            "black_border": False,
            "no_geraldo": False,
            "lcc": {"leftover": 1},
            "format": 1,
        }
    return make
