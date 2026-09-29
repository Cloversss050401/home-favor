"""AI 食谱生成相关 DTO：三层结果（共享菜品 / 个人分餐+营养评估 / 采购清单）。

对齐硬性业务规则第 2、5 条：
- 大模型强制输出 JSON，后端解析后经 nutrition_service 本地二次校验
- 采购清单由 purchase_service 按缺口触发
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shopping_list.schemas import PurchaseItem


class RecipeGenerateRequest(BaseModel):
    family_id: int = Field(default=1, gt=0)
    dish_count: int = Field(default=4, ge=2, le=10, description="期望菜品数量")
    buy_supplement: bool = Field(
        default=True,
        description="食材模式：True=现有食材+推荐采购（默认）；False=仅用现有食材",
    )
    meal_type: str = Field(
        default="",
        description="餐次：breakfast/lunch/dinner/snack；空=不限餐次按全天目标",
    )


class SharedDish(BaseModel):
    """全家共享菜品。"""

    name: str
    category: str = Field(default="main", description="main/staple/soup/dessert")
    is_main_dish: bool = True
    main_ingredients: list[str] = Field(default_factory=list)
    cooking_method: str = ""
    estimated_servings: int = 1
    note: str = ""
    suitable_member_ids: list[int] = Field(
        default_factory=list,
        description="适合的成员 id（模型可输出，后端以规则二次校验为准）",
    )
    needs_purchase: bool = Field(
        default=False, description="该菜是否包含需采购食材（🛒需采购 / ✅已有食材）"
    )
    purchase_ingredients: list[str] = Field(
        default_factory=list, description="该菜需要采购的食材清单（家中没有的）"
    )


class MemberAllocation(BaseModel):
    """个人分餐方案 + 双维度营养评估。"""

    member_id: int
    member_name: str
    dishes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="该成员每道菜的分配（dish_name / amount_g）",
    )
    intake_advantage: list[str] = Field(
        default_factory=list, description="摄入优点：匹配个人体质/健康目标"
    )
    cooking_tips: list[str] = Field(
        default_factory=list,
        description="烹饪提示（如婴幼儿低盐少油、软烂好嚼）",
    )
    nutrition_gap: list[dict[str, Any]] = Field(
        default_factory=list,
        description="营养缺口：nutrient / rni / actual / gap_ratio / status / advice",
    )


class RecipeGenerateResult(BaseModel):
    """生成食谱三层结果（snapshot 落库）。"""

    shared_dishes: list[SharedDish]
    member_allocation: list[MemberAllocation]
    purchase_list: list[PurchaseItem] = Field(default_factory=list)
    tip: str = Field(
        default="",
        description="生成提示：仅现有食材且数量不足时提示可开启采购补齐（前端弹窗用）",
    )


class RecipeGenerateResponse(BaseModel):
    record_id: int
    family_id: int
    result: RecipeGenerateResult
    created_at: datetime


class RecipeRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    input_snapshot: dict[str, Any]
    meal_type: str = ""
    shared_dishes: list[dict[str, Any]]
    member_allocation: list[dict[str, Any]]
    purchase_list: list[dict[str, Any]]
    created_at: datetime


class RecipeRecordListOut(BaseModel):
    total: int
    items: list[RecipeRecordOut]
