"""家庭成员档案表。

约束（对齐业务规则）：
- 单家庭最多 8 位成员（service 层校验）
- 年龄 0-120，允许婴儿小数（如 8 月龄 0.67）
- 性别枚举；饮食目标单选；体质/健康状况多选（JSON 数组）
- 过敏原：枚举 + 自定义输入（JSON 数组）；忌口：自定义文本数组（JSON）
- 删除使用逻辑删除 is_deleted（0 正常 / 1 删除），禁止物理删除
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class FamilyMember(Base):
    __tablename__ = "family_member"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)          # 姓名 ≤ 20 字符
    age: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)    # 0-120，允许小数
    gender: Mapped[str] = mapped_column(String(10), nullable=False)        # 性别枚举
    diet_goal: Mapped[str] = mapped_column(String(20), nullable=False)     # 饮食目标单选
    constitution: Mapped[list] = mapped_column(                            # 体质多选
        JSON, default=list, nullable=False
    )
    health_conditions: Mapped[list] = mapped_column(                       # 慢病倾向多选
        JSON, default=list, nullable=False
    )
    allergens: Mapped[list] = mapped_column(                               # 过敏原：枚举+自定义
        JSON, default=list, nullable=False
    )
    dietary_restrictions: Mapped[list] = mapped_column(                    # 忌口文本数组
        JSON, default=list, nullable=False
    )
    is_deleted: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True                    # 0 正常 / 1 已删除
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FamilyMember id={self.id} name={self.name}>"