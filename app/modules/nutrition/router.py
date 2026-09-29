"""用户反馈路由。

对齐硬性业务规则第 4 条：
- 手动输入优先级更高；use_ai_amount 一键全选复用 AI 分配分量
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.nutrition.schemas import FeedbackCreate, FeedbackListOut, FeedbackOut
from app.modules.nutrition.service import FeedbackService

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


"""周度营养报告路由。

对齐硬性业务规则第 4 条：
- 只统计有反馈记录的天数，空白不估算
- 超标 = 实际摄入 > 1.2×RNI；达标率 = 总摄入/(RNI×有效天数)×100%
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.nutrition.schemas import (
    ReportGenerateRequest,
    ReportListOut,
    ReportOut,
)
from app.modules.nutrition.service import ReportService
from app.common.utils import export_report_xlsx

report_router = APIRouter(prefix="/api/reports", tags=["周度报告"])


@report_router.post("/generate", response_model=ReportOut, summary="生成周报")
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


@report_router.get("", response_model=ReportListOut, summary="周报历史")
def list_reports(family_id: int = 1, db: Session = Depends(get_db)) -> ReportListOut:
    reports = ReportService(db).list_reports(family_id)
    return ReportListOut(
        total=len(reports), items=[ReportOut.model_validate(r) for r in reports]
    )


@report_router.delete("/{report_id}", summary="删除周报")
def delete_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    """删除一条历史周报（产物删除，不影响反馈/食谱/采购数据）。"""
    ok = ReportService(db).delete_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="周报记录不存在")
    return {"ok": True}


@report_router.get("/export", summary="导出周报 Excel")
def export_report(
    report_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """按周报记录导出 Excel（xlsx）：周报明细 + 成员问题汇总两个 sheet。

    前端周报表格与采购清单一致，提供一键导出本地表格的能力。
    """
    report = ReportService(db).get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="周报记录不存在")
    file_name = f"weekly_report_{report.id}.xlsx"
    path = export_report_xlsx(report.report_data, file_name=file_name)
    return {
        "ok": True,
        "file_name": file_name,
        "path": path,
        "rows": len(report.report_data.get("members", [])),
    }

# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router, report_router]
