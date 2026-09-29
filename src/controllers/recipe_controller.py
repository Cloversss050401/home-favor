"""AI 食谱生成路由：生成 / 记录查询。

对齐硬性业务规则第 5 条：
- LLM 强制 JSON 输出，service 层本地二次校验营养
- 生成 + 采购联动：触发条件满足时附带采购清单，全量落库
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.exceptions.business_exception import LLMJsonParseError, LLMTimeoutError
from src.repository.db_session import get_db
from src.schemas.recipe_schema import (
    RecipeGenerateRequest,
    RecipeGenerateResponse,
    RecipeGenerateResult,
    RecipeRecordListOut,
    RecipeRecordOut,
)
from src.services.purchase_service import PurchaseService
from src.services.recipe_service import RecipeService

router = APIRouter(prefix="/api/recipes", tags=["AI 食谱"])


@router.post("/generate", response_model=RecipeGenerateResponse, summary="AI 生成食谱（含采购联动）")
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

    # 采购联动：触发条件满足则生成采购清单
    purchase_svc = PurchaseService(db)
    purchase_items = purchase_svc.build_purchase_list(payload.family_id, result)
    result.purchase_list = purchase_items

    record = recipe_svc.persist(payload.family_id, result)
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


@router.get("/{record_id}", response_model=RecipeRecordOut, summary="生成记录详情")
def get_record(record_id: int, db: Session = Depends(get_db)) -> RecipeRecordOut:
    recipe_svc = RecipeService(db)
    record = recipe_svc.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="食谱记录不存在")
    return RecipeRecordOut.model_validate(record)