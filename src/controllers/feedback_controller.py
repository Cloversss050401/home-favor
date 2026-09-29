"""用户反馈路由。

对齐硬性业务规则第 4 条：
- 手动输入优先级更高；use_ai_amount 一键全选复用 AI 分配分量
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.repository.db_session import get_db
from src.schemas.feedback_schema import FeedbackCreate, FeedbackListOut, FeedbackOut
from src.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/feedback", tags=["用户反馈"])


@router.post("", status_code=201, summary="提交当日反馈")
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> dict:
    count = FeedbackService(db).create_feedback(payload)
    return {"ok": True, "affected": count}


@router.get("", response_model=FeedbackListOut, summary="反馈列表")
def list_feedback(
    family_id: int = 1,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> FeedbackListOut:
    from datetime import timedelta

    _end = end or date.today()
    _start = start or (_end - timedelta(days=30))
    rows = FeedbackService(db).list_feedback(family_id, _start, _end)
    return FeedbackListOut(
        total=len(rows), items=[FeedbackOut.model_validate(r) for r in rows]
    )