import pytest

from app.services.profile_logic import parse_profile_facts  # updated import


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "I am a 45 year old male, 80 kg, 180 cm tall and moderate activity.",
            {
                "sex": "male",
                "age": 45.0,
                "weight_kg": 80.0,
                "height_cm": 180.0,
                "activity_factor": 1.55,
            },
        ),
        (
            "I'm a 30 yo female at 150 lbs and 5'6\" with light activity.",
            {
                "sex": "female",
                "age": 30.0,
                # 150 lb -> kg
                "weight_kg": 150 * 0.4536,
                # 5'6" -> 66 in -> 167.64 cm
                "height_cm": (5 * 12 + 6) * 2.54,
                "activity_factor": 1.375,
            },
        ),
        (
            "Female 40 yrs, 170 cm, 160 lbs, very active at work.",
            {
                "sex": "female",
                "age": 40.0,
                "weight_kg": 160 * 0.4536,
                "height_cm": 170.0,
                "activity_factor": 1.725,
            },
        ),
        (
            "Just started lifting, male.",
            {
                "sex": "male",
                "age": None,
                "weight_kg": None,
                "height_cm": None,
                "activity_factor": 1.2,  # lifting alone infers sedentary (default from heuristic)
            },
        ),
    ],
)
def test_parse_profile_facts(message, expected):
    facts = parse_profile_facts(message)
    # Check each expected field (floats approximately)
    for k, v in expected.items():
        if isinstance(v, float):
            assert facts[k] == pytest.approx(v, rel=1e-3)
        else:
            assert facts[k] == v
    # Unspecified fields should still exist
    for field in ["sex", "age", "weight_kg", "height_cm", "activity_factor"]:
        assert field in facts

