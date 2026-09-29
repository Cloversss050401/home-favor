"""食物成分表仓库：纯数据存取；配合 Redis 缓存供营养计算高频读取。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.food_nutrition_model import FoodNutrition


class FoodNutritionRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, food_name: str) -> FoodNutrition | None:
        stmt = select(FoodNutrition).where(
            FoodNutrition.food_name == food_name
        )
        return self.db.scalars(stmt).first()

    def get_by_names(self, names: list[str]) -> list[FoodNutrition]:
        stmt = select(FoodNutrition).where(FoodNutrition.food_name.in_(names))
        return list(self.db.scalars(stmt))

    def all(self) -> list[FoodNutrition]:
        return list(self.db.scalars(select(FoodNutrition)))

    def upsert(self, rows: list[dict]) -> None:
        """批量导入数据（食物成分表初始化）。"""
        for row in rows:
            existing = self.get_by_name(row["food_name"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
                self.db.add(existing)
            else:
                self.db.add(FoodNutrition(**row))
        self.db.commit()