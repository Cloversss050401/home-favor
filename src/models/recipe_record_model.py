"""AI 食谱生成记录表。

保存每次生成的三层结果（共享菜品、个人分餐方案、采购清单）及输入快照，
作为反馈折算、周报统计与历史追溯的数据源。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class RecipeGenerationRecord(Base):
    __tablename__ = "recipe_generation_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # 输入快照：参与生成的成员档案 + 食材列表
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # 一、全家共享菜品清单
    shared_dishes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # 二、个人分餐方案 + 双维度营养评估（摄入优点 / 营养缺口）
    member_allocation: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # 三、食材不足智能采购清单（可能为空 = 未触发）
    purchase_list: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RecipeGenerationRecord id={self.id} family={self.family_id}>"