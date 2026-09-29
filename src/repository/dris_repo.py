"""DRIs 参考摄入量仓库：纯数据存取；配合 Redis 缓存供营养计算高频读取。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.dris_model import DrisStandard


class DrisRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(
        self, target_type: str, nutrient_code: str
    ) -> DrisStandard | None:
        stmt = select(DrisStandard).where(
            DrisStandard.target_type == target_type,
            DrisStandard.nutrient_code == nutrient_code,
        )
        return self.db.scalars(stmt).first()

    def list_by_target(self, target_type: str) -> list[DrisStandard]:
        stmt = select(DrisStandard).where(
            DrisStandard.target_type == target_type
        )
        return list(self.db.scalars(stmt))

    def upsert(self, rows: list[dict]) -> None:
        """批量导入数据（DRIs 初始化）。"""
        for row in rows:
            existing = self.get(row["target_type"], row["nutrient_code"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
                self.db.add(existing)
            else:
                self.db.add(DrisStandard(**row))
        self.db.commit()