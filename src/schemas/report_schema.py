"""周度营养报告 DTO：对齐硬性业务规则第 4 条。

- 只统计有反馈记录的天数，空白日期不估算
- 超标判定：实际摄入 > 1.2 × RNI
- 周达标率 = 周实际总摄入 / (RNI × 有效统计天数) × 100%
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WeekRange(BaseModel):
    start: date
    end: date


class ReportGenerateRequest(BaseModel):
    family_id: int = Field(default=1, gt=0)
    week_start: date
    week_end: date
    generate_type: int = Field(default=0, ge=0, le=1, description="0 手动 / 1 自动")


class NutrientSummary(BaseModel):
    nutrient_code: str
    nutrient_name: str
    rni_per_day: Decimal
    effective_days: int
    total_intake: Decimal
    daily_avg: Decimal
    rate: Decimal = Field(description="达标率 = 总摄入/(RNI×有效天数)×100%")
    exceeded: bool = Field(description="实际摄入 > 1.2×RNI 超标")
    gap: Decimal


class MemberWeekSummary(BaseModel):
    member_id: int
    member_name: str
    nutrients: list[NutrientSummary]
    problem_summary: list[str]


class ReportData(BaseModel):
    week_start: date
    week_end: date
    effective_days: int
    members: list[MemberWeekSummary]
    weekly_tips: list[str] = Field(default_factory=list, description="下周建议")


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    week_start: date
    week_end: date
    generate_type: int
    report_data: dict[str, Any]
    created_at: datetime


class ReportListOut(BaseModel):
    total: int
    items: list[ReportOut]