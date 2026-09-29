"""采购清单相关 DTO：由原 recipe_schema 拆出（对齐 shopping_list 模块）。"""

from decimal import Decimal

from pydantic import BaseModel, Field


class PurchaseItem(BaseModel):
    priority: str = "P0"  # P0/P1/P2
    food_name: str
    supplement_nutrient: list[str] = Field(default_factory=list)
    suggest_amount_g: Decimal
    remark: str = ""
    # 前端契约列（采购清单/导出）：优先补齐成员 + 缺口比例
    target_member: str = ""  # 优先补齐成员姓名（无则空）
    gap_ratio: float = 0  # 缺口比例 %（该成员最严重核心营养素缺口）
    # 历史联动必买：连续 N 天同一营养素缺口>30% 升级为必买项（★）
    is_must_buy: bool = False


class PurchaseExportOut(BaseModel):
    ok: bool = True
    file_name: str
    rows: int
