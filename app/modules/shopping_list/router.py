"""采购清单路由：触发生成 / Excel 导出。

对齐硬性业务规则第 2 条：
- 触发条件：任意成员核心营养素缺口>30% 或 主菜<2
- 采购满足全家 3 天需求；已录重量扣减存量、≤0 移除；无重量仅标记
- 导出字段：优先级 / 食材名称 / 补充营养素 / 建议采购量g / 备注
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.recipe.schemas import MemberAllocation, RecipeGenerateResult, SharedDish
from app.modules.shopping_list.schemas import PurchaseExportOut, PurchaseItem
from app.modules.shopping_list.service import PurchaseService

router = APIRouter(prefix="/api/purchase", tags=["智能采购"])


@router.post("/check", summary="检查是否触发采购")
def check_purchase(family_id: int = 1, db: Session = Depends(get_db)) -> dict:
    svc = PurchaseService(db)
    trigger_big_gap = svc.family_has_big_gap(family_id)
    return {
        "family_id": family_id,
        "triggered": trigger_big_gap,
        "reason": "核心营养素缺口>30%" if trigger_big_gap else "未触发",
    }


@router.post("/export", response_model=PurchaseExportOut, summary="导出采购清单 Excel")
def export_purchase(
    fmt: str = "xlsx",
    family_id: int = 1,
    db: Session = Depends(get_db),
) -> PurchaseExportOut:
    """基于最新食谱生成记录重建采购清单并导出 xlsx/csv。

    无记录时返回空清单（触发判定依赖字典表，无食谱记录时按缺口静态推荐）。
    """
    svc = PurchaseService(db)
    record = svc.latest_record(family_id)
    if record is None or not record.shared_dishes:
        rows = 0
        file_name = f"purchase_list_{date.today():%Y%m%d}.{fmt}"
        svc.export_excel([], fmt=fmt)
        return PurchaseExportOut(file_name=file_name, rows=rows)

    result = RecipeGenerateResult(
        shared_dishes=[SharedDish.model_validate(d) for d in record.shared_dishes],
        member_allocation=[
            MemberAllocation.model_validate(m) for m in record.member_allocation
        ],
        purchase_list=[PurchaseItem.model_validate(p) for p in record.purchase_list],
    )
    items = svc.build_purchase_list(family_id, result)
    file_name = f"purchase_list_{date.today():%Y%m%d}.{fmt}"
    svc.export_excel(items, fmt=fmt)
    return PurchaseExportOut(file_name=file_name, rows=len(items))

# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router]
