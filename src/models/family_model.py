"""家庭表：一个家庭（默认单家庭，为二期多家庭预留）。

修复记录（DEF-01）：补 is_deleted 逻辑删除字段，对齐硬性业务规则
"删除使用 is_deleted 逻辑删除，禁止物理删除"，并为二期多家庭预留删除语义。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


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
