"""用户反馈 DTO：对齐硬性业务规则第 4 条。

- 反馈：勾选实际制作菜品 + 各成员实际食用分量
- 一键全选（use_ai_amount=True）：复用 AI 推荐的分配分量；手动输入优先级更高
- 每餐条目：member_id + dish_name + amount_g
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackItem(BaseModel):
    member_id: int = Field(gt=0)
    dish_name: str = Field(min_length=1, max_length=100)
    amount_g: Decimal | None = Field(default=None, gt=0, description="实际食用分量 g")


class FeedbackCreate(BaseModel):
    family_id: int = Field(default=1, gt=0)
    recipe_record_id: int | None = Field(default=None, description="关联食谱生成记录")
    eaten_date: date
    # True=一键全选：从关联记录（或最新记录）按成员复制 AI 分配分量
    use_ai_amount: bool = False
    # 手动输入明细：手动输入优先级更高（amount_g 必填）
    items: list[FeedbackItem] = Field(min_length=1, max_length=200)

    def manual_items(self) -> list[FeedbackItem]:
        return [it for it in self.items if it.amount_g is not None]


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    recipe_record_id: int | None
    member_id: int
    dish_name: str
    amount_g: Decimal
    eaten_date: date
    is_ai_recommended: int


class FeedbackListOut(BaseModel):
    total: int
    items: list[FeedbackOut]