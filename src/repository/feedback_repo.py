"""用户反馈仓库：纯数据存取。"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.feedback_model import UserFeedback


class FeedbackRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(self, items: list[UserFeedback]) -> int:
        self.db.add_all(items)
        self.db.commit()
        return len(items)

    def list_by_range(
        self, family_id: int, start: date, end: date
    ) -> list[UserFeedback]:
        stmt = (
            select(UserFeedback)
            .where(
                UserFeedback.family_id == family_id,
                UserFeedback.eaten_date >= start,
                UserFeedback.eaten_date <= end,
            )
            .order_by(UserFeedback.eaten_date.asc(), UserFeedback.member_id.asc())
        )
        return list(self.db.scalars(stmt))

    def list_dates_in_range(
        self, family_id: int, start: date, end: date
    ) -> set[date]:
        """统计有效反馈日期集合（周报只统计有记录的天数）。"""
        stmt = select(UserFeedback.eaten_date).where(
            UserFeedback.family_id == family_id,
            UserFeedback.eaten_date >= start,
            UserFeedback.eaten_date <= end,
        )
        return {row for row in self.db.scalars(stmt)}