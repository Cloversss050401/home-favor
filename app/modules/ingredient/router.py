"""食材录入路由：文字（单条/批量）+ 人工确认入库。

对齐硬性业务规则第 1 条：
- 名称必填、重量选填；"番茄 500g"自动拆分
- 识别结果必须人工确认后才进入业务流程（confirm_and_save 是唯一入库入口）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.ingredient.schemas import (
    IngredientClearOut,
    IngredientConfirmIn,
    IngredientCreate,
    IngredientListOut,
    IngredientOut,
    IngredientRecognizeResult,
    IngredientUpdate,
)
from app.modules.ingredient.service import IngredientService

router = APIRouter(prefix="/api/ingredients", tags=["食材录入"])


@router.post("/text", response_model=IngredientRecognizeResult, summary="文字录入（自动拆分）")
def recognize_text(
    payload: IngredientCreate, db: Session = Depends(get_db)
) -> IngredientRecognizeResult:
    """单条文字录入：如 "番茄 500g"（名称+重量自动拆分）或 "鸡胸肉"（无重量）。"""
    svc = IngredientService(db)
    try:
        items = svc.recognize_by_text([payload.name])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not items:
        raise HTTPException(status_code=400, detail="未识别到食材名称")
    item = items[0]
    # 保留用户直接提交的重量（若 payload 已带重量则覆盖解析结果）
    if payload.available_weight is not None:
        item.available_weight = payload.available_weight
    return IngredientRecognizeResult(recognized=[item])


@router.post("/text/batch", response_model=IngredientRecognizeResult, summary="文字批量录入")
def recognize_text_batch(
    texts: list[str], db: Session = Depends(get_db)
) -> IngredientRecognizeResult:
    """批量文字录入：每行一条；支持标点分隔的连续文本。"""
    svc = IngredientService(db)
    try:
        items = svc.recognize_by_text(texts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngredientRecognizeResult(recognized=items)



@router.post("/confirm", status_code=201, summary="人工确认后入库")
def confirm_ingredients(
    payload: IngredientConfirmIn, db: Session = Depends(get_db)
) -> dict:
    """人工确认前一步识别结果：可删错补漏、修改重量，确认后批量入库。"""
    count = IngredientService(db).confirm_and_save(payload)
    return {"ok": True, "affected": count}


@router.get("", response_model=IngredientListOut, summary="家中食材列表")
def list_ingredients(db: Session = Depends(get_db)) -> IngredientListOut:
    svc = IngredientService(db)
    items = svc.list_ingredients()
    return IngredientListOut(total=len(items), items=[IngredientOut.model_validate(i) for i in items])


@router.put("/{item_id}", response_model=IngredientOut, summary="修改食材")
def update_ingredient(
    item_id: int, payload: IngredientUpdate, db: Session = Depends(get_db)
) -> IngredientOut:
    item = IngredientService(db).update_ingredient(
        item_id,
        name=payload.name,
        available_weight=payload.available_weight,
        weight_unit=payload.weight_unit,
    )
    return IngredientOut.model_validate(item)


@router.delete("/{item_id}", response_model=IngredientOut, summary="删除食材（失效标记）")
def delete_ingredient(item_id: int, db: Session = Depends(get_db)) -> IngredientOut:
    item = IngredientService(db).delete_ingredient(item_id)
    return IngredientOut.model_validate(item)


@router.post("/clear", response_model=IngredientClearOut, summary="清空全家食材")
def clear_ingredients(db: Session = Depends(get_db)) -> IngredientClearOut:
    affected = IngredientService(db).clear_ingredients()
    return IngredientClearOut(affected=affected)

# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router]
