"""AI 食谱生成路由：生成 / 记录查询。

对齐硬性业务规则第 5 条：
- LLM 强制 JSON 输出，service 层本地二次校验营养
- 生成 + 采购联动：触发条件满足时附带采购清单，全量落库
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import LLMJsonParseError, LLMTimeoutError
from app.common.deps import get_db
from app.modules.recipe.schemas import (
    RecipeGenerateRequest,
    RecipeGenerateResponse,
    RecipeGenerateResult,
    RecipeRecordListOut,
    RecipeRecordOut,
)
from app.modules.shopping_list.service import PurchaseService
from app.modules.recipe.service import RecipeService

router = APIRouter(prefix="/api/recipes", tags=["AI 食谱"])


@router.post(
    "/generate",
    response_model=RecipeGenerateResponse,
    summary="AI 生成食谱（含采购联动）",
)
def generate_recipe(
    payload: RecipeGenerateRequest, db: Session = Depends(get_db)
) -> RecipeGenerateResponse:
    recipe_svc = RecipeService(db)
    try:
        result: RecipeGenerateResult = recipe_svc.generate(payload)
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message)
    except LLMJsonParseError as exc:
        raise HTTPException(status_code=502, detail=exc.message)

    # 采购联动：补菜缺料清单（service 已生成）与缺口触发清单合并
    purchase_svc = PurchaseService(db)
    gap_items = purchase_svc.build_purchase_list(payload.family_id, result)
    result.purchase_list = PurchaseService.merge_items(
        list(result.purchase_list) + list(gap_items)
    )

    record = recipe_svc.persist(
        payload.family_id, result, meal_type=payload.meal_type or ""
    )
    return RecipeGenerateResponse(
        record_id=record.id,
        family_id=record.family_id,
        result=result,
        created_at=record.created_at,
    )


@router.get("/records", response_model=RecipeRecordListOut, summary="生成历史")
def list_records(
    family_id: int = 1, limit: int = 50, db: Session = Depends(get_db)
) -> RecipeRecordListOut:
    recipe_svc = RecipeService(db)
    records = recipe_svc.list_records(family_id, limit=limit)
    return RecipeRecordListOut(
        total=len(records), items=[RecipeRecordOut.model_validate(r) for r in records]
    )


# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router]
