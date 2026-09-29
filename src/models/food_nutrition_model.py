"""中国食物成分表（字典表）。

存储常见食材每 100g 可食部的营养成分，是营养计算与本地二次校验的唯一权威数据源。
营养成分单位统一约定：
- protein/脂肪/碳水：g/100g
- calcium/iron/zinc/vitamin_a/vitamin_c：mg/100g
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class FoodNutrition(Base):
    __tablename__ = "food_nutrition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    food_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    food_category: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    # 核心 6 项（参与采购触发）
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)   # g/100g
    calcium: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)  # mg/100g
    iron: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)     # mg/100g
    zinc: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)     # mg/100g
    vitamin_a: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)  # mg/100g
    vitamin_c: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)  # mg/100g

    # 展示用扩展营养素（不触发采购）
    energy: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)  # kcal/100g
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)      # g/100g
    carbohydrate: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)  # g/100g
    per_amount_g: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=100, nullable=False                         # 表中该行对应的食物量
    )

    remark: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FoodNutrition name={self.food_name}>"