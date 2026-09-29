"""通用工具：日期工具（周统计窗口、日期范围）。"""
from datetime import date, timedelta


def monday_of_week(day: date) -> date:
    """返回所在周的周一（ISO 周起始）。"""
    return day - timedelta(days=day.weekday())


def week_range(day: date) -> tuple[date, date]:
    """返回 (周一, 周日)。"""
    monday = monday_of_week(day)
    return monday, monday + timedelta(days=6)


def date_list(start: date, end: date) -> list[date]:
    """返回闭区间内的日期列表。"""
    days = (end - start).days
    if days < 0:
        return []
    return [start + timedelta(days=i) for i in range(days + 1)]


def effective_days(
    start: date, end: date, recorded_dates: set[date]
) -> list[date]:
    """周报只统计有反馈记录的天数（空白日期不做 AI 估算）。"""
    return [d for d in date_list(start, end) if d in recorded_dates]


def is_weekend(day: date) -> bool:
    """是否周日（自动生成周报的执行判断）。"""
    return day.weekday() == 6