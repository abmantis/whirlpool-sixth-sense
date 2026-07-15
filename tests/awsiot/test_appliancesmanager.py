import pytest

from whirlpool.awsiot.appliancesmanager import _is_dryer_model


@pytest.mark.parametrize(
    ("model_number", "expected"),
    [
        ("MGD7020RF0", True),  # Maytag gas dryer
        ("MED7020RF0", True),  # Maytag electric dryer
        ("WGD5620HW1", True),  # Whirlpool gas dryer
        ("MFW7020RF0", False),  # Maytag front-load washer
        ("MHW6630HW0", False),  # Maytag front-load washer
        ("WTW5010LW0", False),  # Whirlpool top-load washer
        ("", False),
        ("MF", False),
    ],
)
def test_is_dryer_model(model_number: str, expected: bool) -> None:
    assert _is_dryer_model(model_number) is expected
