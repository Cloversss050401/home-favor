"""DRIs 中国居民膳食营养素参考摄入量（字典表）。

按目标人群类型 + 营养素维护每日推荐摄入值（RNI），
是营养缺口计算、采购量计算、周报达标率判定的基准。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


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