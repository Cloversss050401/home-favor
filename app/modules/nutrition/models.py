"""DRIs 中国居民膳食营养素参考摄入量（字典表）。

按目标人群类型 + 营养素维护每日推荐摄入值（RNI），
是营养缺口计算、采购量计算、周报达标率判定的基准。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DrisStandard(Base):
    __tablename__ = "dris_standard"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # 人群类别：adult_male/adult_female/slim/muscle/pregnant/baby_6_12m/elderly 等
    nutrient_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # protein/calcium/iron/zinc/vitamin_a/vitamin_c 等
    nutrient_name: Mapped[str] = mapped_column(String(20), nullable=False)
    rni_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # 每日推荐值
    unit: Mapped[str] = mapped_column(String(10), nullable=False)               # g / mg
    applicable_age: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    remark: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DrisStandard {self.target_type}/{self.nutrient_code}="
            f"{self.rni_value}{self.unit}>"
        )


from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


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


from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

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
    meal_type: Mapped[str] = mapped_column(  # 餐次（早餐/午餐/晚餐/加餐；空=不限）
        String(10), default="", nullable=False
    )
    custom_ingredients: Mapped[Optional[list]] = mapped_column(  # 自定义菜品主料（可选）
        JSON, default=list, nullable=True
    )
    is_ai_recommended: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False                                # 1=一键全选复用AI分量
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserFeedback id={self.id} member={self.member_id} dish={self.dish_name}>"


from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


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
