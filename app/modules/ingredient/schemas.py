"""食材录入 DTO：对齐硬性业务规则第 1 条。

- 食材名称必填；可用重量选填（available_weight 可 None，单位默认 g）
- 支持"番茄 500g"自动拆分（text 录入由 service 调用 weight_parser）
- 识别结果必须经人工确认（recognized -> confirm）
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import model_validator

from app.core.constants import INGREDIENT_WEIGHT_UNIT


class IngredientCreate(BaseModel):
    family_id: int = Field(default=1, gt=0)
    name: str = Field(min_length=1, max_length=50)
    available_weight: Decimal | None = Field(
        default=None, ge=0, description="可用重量，选填"
    )
    weight_unit: str = Field(default=INGREDIENT_WEIGHT_UNIT, max_length=10)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("食材名称不能为空")
        return v


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    available_weight: Decimal | None = Field(default=None, ge=0)
    weight_unit: str | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def _at_least_one(self) -> "IngredientUpdate":
        if (
            self.name is None
            and self.available_weight is None
            and self.weight_unit is None
        ):
            raise ValueError("至少提供一个待更新字段")
        return self


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    name: str
    available_weight: Decimal | None
    weight_unit: str
    is_valid: int
    created_at: datetime
    updated_at: datetime


class IngredientListOut(BaseModel):
    total: int
    items: list[IngredientOut]


class IngredientRecognizeItem(BaseModel):
    """识别出的单条食材（待人工确认）。"""

    name: str
    available_weight: Decimal | None = None
    weight_unit: str = INGREDIENT_WEIGHT_UNIT


class IngredientRecognizeResult(BaseModel):
    """拍照 / 语音识别返回：识别列表 + 提示人工确认。"""

    recognized: list[IngredientRecognizeItem]
    need_confirm: bool = True


class IngredientConfirmIn(BaseModel):
    """人工确认后的最终食材列表：用户可删错补漏、修改重量。"""

    family_id: int = Field(default=1, gt=0)
    items: list[IngredientCreate] = Field(
        min_length=1, max_length=200, description="确认后的食材列表"
    )


class IngredientClearOut(BaseModel):
    ok: bool = True
    affected: int