import pytest

from app.services.profile_logic import compute_tdee  # updated import


@pytest.mark.parametrize(
    "profile,expected_sex",
    [
        (
            {
                "sex": "male",
                "age": 45.0,
                "weight_kg": 80.0,
                "height_cm": 180.0,
                "activity_factor": 1.55,
            },
            "male",
        ),
        (
            {
                "sex": "female",
                "age": 30.0,
                "weight_kg": 65.0,
                "height_cm": 165.0,
                "activity_factor": 1.375,
            },
            "female",
        ),
    ],
)
def test_compute_tdee_basic(profile, expected_sex):
    res = compute_tdee(profile)
    assert set(res.keys()) == {"bmr", "tdee_low", "tdee_high"}
    # monotonic band
    assert res["tdee_low"] <= res["tdee_high"]
    # check plausible range
    assert 800 < res["bmr"] < 3000


@pytest.mark.parametrize(
    "profile,expected_bmr",
    [
        # Male edge age (young adult) using Mifflin St Jeor formula
        (
            {
                "sex": "male",
                "age": 18.0,
                "weight_kg": 60.0,
                "height_cm": 170.0,
                "activity_factor": 1.2,
            },
            int(round(10 * 60 + 6.25 * 170 - 5 * 18 + 5)),
        ),
        # Female older age
        (
            {
                "sex": "female",
                "age": 65.0,
                "weight_kg": 55.0,
                "height_cm": 160.0,
                "activity_factor": 1.375,
            },
            int(round(10 * 55 + 6.25 * 160 - 5 * 65 - 161)),
        ),
    ],
)
def test_compute_tdee_bmr_exact(profile, expected_bmr):
    res = compute_tdee(profile)
    assert res["bmr"] == expected_bmr


def test_compute_tdee_missing():
    incomplete = {"sex": "male", "age": 40, "weight_kg": 80, "height_cm": None, "activity_factor": 1.2}
    with pytest.raises(ValueError):
        compute_tdee(incomplete)
