"""周度营养报告表。

report_data 保存完整周报 JSON（达标率、累计缺口、超标项、下周建议），
生成模式：手动生成（0）/ 每周日自动生成（1）。
"""
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class WeeklyNutReport(Base):
    __tablename__ = "weekly_nut_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)       # 周一
    week_end: Mapped[date] = mapped_column(Date, nullable=False)         # 周日
    generate_type: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False                               # 0 手动 / 1 自动
    )
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WeeklyNutReport id={self.id} week={self.week_start}~{self.week_end}>"