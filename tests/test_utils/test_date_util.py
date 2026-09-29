"""日期工具测试：周窗口（周一~周日）/ 日期区间 / 有效天数 / 周末判断。"""
from datetime import date

from app.common.utils import (
    date_list,
    effective_days,
    is_weekend,
    monday_of_week,
    week_range,
)


class TestWeekRange:
    def test_monday_of_week(self):
        # 2026-09-25 是周五，所在周周一为 2026-09-21
        assert monday_of_week(date(2026, 9, 25)) == date(2026, 9, 21)

    def test_monday_itself(self):
        assert monday_of_week(date(2026, 9, 21)) == date(2026, 9, 21)

    def test_week_range_monday_to_sunday(self):
        start, end = week_range(date(2026, 9, 25))
        assert start == date(2026, 9, 21)
        assert end == date(2026, 9, 27)


class TestDateList:
    def test_inclusive_range(self):
        days = date_list(date(2026, 9, 21), date(2026, 9, 23))
        assert len(days) == 3
        assert days[0] == date(2026, 9, 21)
        assert days[-1] == date(2026, 9, 23)

    def test_invalid_range_returns_empty(self):
        assert date_list(date(2026, 9, 23), date(2026, 9, 21)) == []

    def test_single_day(self):
        assert date_list(date(2026, 9, 21), date(2026, 9, 21)) == [date(2026, 9, 21)]


class TestEffectiveDays:
    def test_filter_recorded_dates(self):
        recorded = {date(2026, 9, 21), date(2026, 9, 23)}
        result = effective_days(date(2026, 9, 21), date(2026, 9, 27), recorded)
        assert result == [date(2026, 9, 21), date(2026, 9, 23)]

    def test_no_recorded_returns_empty(self):
        assert effective_days(date(2026, 9, 21), date(2026, 9, 27), set()) == []


class TestIsWeekend:
    def test_sunday_is_weekend(self):
        assert is_weekend(date(2026, 9, 27)) is True

    def test_monday_not_weekend(self):
        assert is_weekend(date(2026, 9, 21)) is False