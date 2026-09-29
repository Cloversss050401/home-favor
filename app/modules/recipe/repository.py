"""食谱生成记录仓库：纯数据存取。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.recipe.models import RecipeGenerationRecord


class RecipeRecordRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, record: RecipeGenerationRecord) -> RecipeGenerationRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, record_id: int) -> RecipeGenerationRecord | None:
        return self.db.get(RecipeGenerationRecord, record_id)

    def list_by_family(
        self, family_id: int, limit: int = 50
    ) -> list[RecipeGenerationRecord]:
        stmt = (
            select(RecipeGenerationRecord)
            .where(RecipeGenerationRecord.family_id == family_id)
            .order_by(RecipeGenerationRecord.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def latest(self, family_id: int) -> RecipeGenerationRecord | None:
        stmt = (
            select(RecipeGenerationRecord)
            .where(RecipeGenerationRecord.family_id == family_id)
            .order_by(RecipeGenerationRecord.id.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()