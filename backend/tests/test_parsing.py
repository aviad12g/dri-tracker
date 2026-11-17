import pytest

from dri.parsing import norm_name, parse_count


@pytest.mark.parametrize("text,expected", [
    ("5.79M", 5_790_000), ("112 313", 112_313), ("37.3K", 37_300), ("1,234,567", 1_234_567),
    ("941", 941), ("2.06m", 2_060_000), ("1.2B", 1_200_000_000), ("112 313", 112_313), ("0", 0),
])
def test_parse_count(text, expected):
    assert parse_count(text) == expected


@pytest.mark.parametrize("text", [None, "", "abc", "+5.2%", "@handle", "1.2.3M", "12 videos", "5.79 million"])
def test_parse_count_rejects_non_counts(text):
    assert parse_count(text) is None


def test_norm_name():
    assert norm_name("The Tucker Carlson Show!") == "thetuckercarlsonshow"
