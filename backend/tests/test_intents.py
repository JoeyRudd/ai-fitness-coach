import pytest

from app.services.profile_logic import is_tdee_intent  # updated import


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Can you calculate my calories?", True),
        ("What is my maintenance?", True),
        ("What's a good starting point for daily burn?", True),
        ("Where do I start with calories?", True),
        ("Tell me a workout plan", False),
        ("I like to walk", False),
    ],
)
def test_is_tdee_intent(message, expected):
    assert is_tdee_intent(message) is expected
