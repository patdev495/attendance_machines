import pytest

from features.daily_summary.export_service import (
    _sheet2_headers,
    _sheet1_indicators,
    _sheet1_values,
)


@pytest.fixture
def day_summary():
    return {
        "first": "08:00",
        "last": "17:00",
        "lunch_out_str": "11:30",
        "lunch_in_str": "12:15",
        "lunch_late_minutes": 15,
        "std": 8.0,
        "ot": 1.0,
        "late": 0,
        "early": 0,
        "shift_code": "N",
    }


@pytest.mark.parametrize("view_mode", ["time", "hours", "both"])
def test_sheet1_includes_lunch_taps_with_aligned_values(day_summary, view_mode):
    indicators = _sheet1_indicators(view_mode)
    values = _sheet1_values(day_summary, view_mode)

    assert len(indicators) == len(values)
    assert values[indicators.index("Ra trưa")] == "11:30"
    assert values[indicators.index("Vào trưa")] == "12:15"
    assert values[indicators.index("Ăn trưa quá giờ (phút)")] == 15


def test_sheet2_includes_lunch_late_minutes_column():
    headers = _sheet2_headers()

    assert "Ăn trưa quá giờ (phút)" in headers
    assert headers.index("Ăn trưa quá giờ (phút)") == headers.index("Trạng thái trưa") + 1
