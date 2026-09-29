"""用户反馈 DTO：对齐硬性业务规则第 4 条 + 前端契约适配。

- 反馈：勾选实际制作菜品 + 各成员实际食用分量
- 一键全选（use_ai_amount=True）：复用 AI 推荐的分配分量；手动输入优先级更高
- 每餐条目：member_id + dish_name + amount_g
- 前端契约：成员食用按"比例"提交（ratio：0~1.5，相对整道菜），
  amount_g 与 ratio 二选一；ratio 折算由 service 层用 DISH_SERVING_BASE_G 兜底。
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeedbackItem(BaseModel):
    member_id: int = Field(gt=0)
    dish_name: str = Field(min_length=1, max_length=100)
    amount_g: Decimal | None = Field(default=None, gt=0, description="实际食用分量 g")
    ratio: Decimal | None = Field(
        default=None,
        gt=0,
        le=Decimal("1.5"),
        description="前端契约：该菜整份的食用比例（0~1.5，如 0.5=吃半份）",
    )
    custom_ingredients: list[str] | None = Field(
        default=None,
        description="自定义菜品主料（方案外自做菜时填写，营养按主料折算）",
    )

    @model_validator(mode="after")
    def _amount_or_ratio(self) -> "FeedbackItem":
        # use_ai_amount 场景由 FeedbackCreate 层面放行（复用 AI 分配分量），
        # 单条 item 无分量仅允许出现在该场景，故此处不强制校验；
        # 分量约束统一在 FeedbackCreate._amount_or_ratio 校验。
        return self


class FeedbackCreate(BaseModel):
    family_id: int = Field(default=1, gt=0)
    recipe_record_id: int | None = Field(default=None, description="关联食谱生成记录")
    eaten_date: date
    meal_type: str = Field(
        default="", description="餐次：breakfast/lunch/dinner/snack；空=不限"
    )
    # True=一键全选：从关联记录（或最新记录）按成员复制 AI 分配分量
    use_ai_amount: bool = False
    # 手动输入明细：手动输入优先级更高（amount_g 或 ratio 二选一）
    items: list[FeedbackItem] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _amount_or_ratio(self) -> "FeedbackCreate":
        # 非"一键全选"场景：每条必须提供 amount_g 或 ratio 至少一个
        if not self.use_ai_amount:
            for it in self.items:
                if it.amount_g is None and it.ratio is None:
                    raise ValueError(
                        f"菜品[{it.dish_name}]未填写食用分量：amount_g 与 ratio 至少提供一个"
                    )
        return self

    def manual_items(self) -> list[FeedbackItem]:
        return [
            it for it in self.items if it.amount_g is not None or it.ratio is not None
        ]


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    recipe_record_id: int | None
    member_id: int
    dish_name: str
    amount_g: Decimal
    eaten_date: date
    meal_type: str = ""
    custom_ingredients: list[str] | None = None
    is_ai_recommended: int


class FeedbackListOut(BaseModel):
    total: int
    items: list[FeedbackOut]


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
