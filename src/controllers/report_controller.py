"""周度营养报告路由。

对齐硬性业务规则第 4 条：
- 只统计有反馈记录的天数，空白不估算
- 超标 = 实际摄入 > 1.2×RNI；达标率 = 总摄入/(RNI×有效天数)×100%
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.repository.db_session import get_db
from src.schemas.report_schema import (
    ReportGenerateRequest,
    ReportListOut,
    ReportOut,
)
from src.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["周度报告"])


@router.post("/generate", response_model=ReportOut, summary="生成周报")
def generate_report(
    payload: ReportGenerateRequest, db: Session = Depends(get_db)
) -> ReportOut:
    svc = ReportService(db)
    data = svc.build_report(payload.family_id, payload.week_start, payload.week_end)
    report = svc.save_report(
        payload.family_id,
        payload.week_start,
        payload.week_end,
        data,
        generate_type=payload.generate_type,
    )
    return ReportOut.model_validate(report)


@router.get("", response_model=ReportListOut, summary="周报历史")
def list_reports(family_id: int = 1, db: Session = Depends(get_db)) -> ReportListOut:
    reports = ReportService(db).list_reports(family_id)
    return ReportListOut(total=len(reports), items=[ReportOut.model_validate(r) for r in reports])