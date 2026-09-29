"""家庭现有食材表。
约束（对齐业务规则）：
- 食材名称必填；可用重量选填（available_weight 可 NULL）
- 单位默认 g
- 一期不做食材消耗自动扣减，食材由用户手动维护
- 删除采用 is_valid 标记失效（0 失效 / 1 有效），不使用物理删除
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class HouseholdIngredient(Base):
    __tablename__ = "household_ingredient"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 食材名称
    available_weight: Mapped[Optional[Decimal]] = mapped_column(                  # 可用重量（选填）
        Numeric(10, 2), nullable=True
    )
    weight_unit: Mapped[str] = mapped_column(String(10), default="g", nullable=False)
    is_valid: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True                       # 1 有效 / 0 失效
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HouseholdIngredient id={self.id} name={self.name}>"
