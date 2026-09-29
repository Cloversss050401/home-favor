"""用户做菜反馈表。
记录每次反馈的明细（成员 + 菜品 + 实际食用分量），是周报折算的原始输入：
user_feedback → 菜品食材配比分解 → 查食物成分表 → 单餐营养素 → 按天/按周聚合。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.models import Base

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recipe_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recipe_generation_record.id", ondelete="SET NULL"),
        nullable=True,
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("family_member.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dish_name: Mapped[str] = mapped_column(String(100), nullable=False)   # 实际制作菜品
    amount_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # 食用分量 g
    eaten_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)  # 食用日期
    is_ai_recommended: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False                                # 1=一键全选复用AI分量
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserFeedback id={self.id} member={self.member_id} dish={self.dish_name}>"
