"""家庭表：一个家庭（默认单家庭，为二期多家庭预留）。

修复记录（DEF-01）：补 is_deleted 逻辑删除字段，对齐硬性业务规则
"删除使用 is_deleted 逻辑删除，禁止物理删除"，并为二期多家庭预留删除语义。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Family(Base):
    __tablename__ = "family"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), default="我的家庭")
    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        index=True,
        comment="0 正常 / 1 逻辑删除",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Family id={self.id} name={self.name}>"



from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FamilyMember(Base):
    __tablename__ = "family_member"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)  # 姓名 ≤ 20 字符
    role: Mapped[str] = (
        mapped_column(  # 家庭角色（前端契约：adult/elders/child/teen/baby/pregnant）
            String(20), default="", nullable=False
        )
    )
    traits: Mapped[list] = (
        mapped_column(  # 饮食特征多选（已弃用，保留列兼容历史数据）
            JSON, default=list, nullable=False
        )
    )
    height_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="身高（cm），可空"
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="体重（kg），可空"
    )
    activity: Mapped[str] = mapped_column(
        String(10), default="light", nullable=False,
        comment="活动水平 sedentary/light/moderate/heavy",
    )
    age: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )  # 0-120，允许小数
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # 性别枚举
    diet_goal: Mapped[str] = mapped_column(String(20), nullable=False)  # 饮食目标单选
    dietary_needs: Mapped[list] = mapped_column(  # 附加需求多选（叠加在主目标之上）
        JSON, default=list, nullable=False
    )
    avoid: Mapped[str] = mapped_column(  # 其他忌口文本（前端契约）
        String(200), default="", nullable=False
    )
    constitution: Mapped[list] = mapped_column(  # 体质多选
        JSON, default=list, nullable=False
    )
    health_conditions: Mapped[list] = mapped_column(  # 慢病倾向多选
        JSON, default=list, nullable=False
    )
    allergens: Mapped[list] = mapped_column(  # 过敏原：枚举+自定义
        JSON, default=list, nullable=False
    )
    dietary_restrictions: Mapped[list] = mapped_column(  # 忌口文本数组
        JSON, default=list, nullable=False
    )
    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,  # 0 正常 / 1 已删除
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FamilyMember id={self.id} name={self.name}>"
