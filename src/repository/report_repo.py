"""周报仓库：纯数据存取。"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.report_model import WeeklyNutReport


class ReportRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: WeeklyNutReport) -> WeeklyNutReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get(self, report_id: int) -> WeeklyNutReport | None:
        return self.db.get(WeeklyNutReport, report_id)

    def list_by_family(
        self, family_id: int, limit: int = 20
    ) -> list[WeeklyNutReport]:
        stmt = (
            select(WeeklyNutReport)
            .where(WeeklyNutReport.family_id == family_id)
            .order_by(WeeklyNutReport.week_start.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def latest(self, family_id: int) -> WeeklyNutReport | None:
        stmt = (
            select(WeeklyNutReport)
            .where(WeeklyNutReport.family_id == family_id)
            .order_by(WeeklyNutReport.week_start.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()