"""家庭食材仓库：纯数据存取，无业务判断。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import INGREDIENT_INVALID, INGREDIENT_IS_VALID
from app.modules.ingredient.models import HouseholdIngredient


class IngredientRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, item: HouseholdIngredient) -> HouseholdIngredient:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_many(self, items: list[HouseholdIngredient]) -> int:
        self.db.add_all(items)
        self.db.commit()
        return len(items)

    def update(self, item: HouseholdIngredient) -> HouseholdIngredient:
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, item_id: int) -> HouseholdIngredient | None:
        return self.db.get(HouseholdIngredient, item_id)

    def list_valid(self, family_id: int) -> list[HouseholdIngredient]:
        stmt = (
            select(HouseholdIngredient)
            .where(
                HouseholdIngredient.family_id == family_id,
                HouseholdIngredient.is_valid == INGREDIENT_IS_VALID,
            )
            .order_by(HouseholdIngredient.id.asc())
        )
        return list(self.db.scalars(stmt))

    def soft_delete(self, item: HouseholdIngredient) -> HouseholdIngredient:
        """标记失效（is_valid=0），不使用物理删除。"""
        item.is_valid = INGREDIENT_INVALID
        self.db.commit()
        self.db.refresh(item)
        return item

    def invalidate_family_items(self, family_id: int) -> int:
        """清空全家食材：批量标记失效。返回失效条数。"""
        stmt = select(HouseholdIngredient).where(
            HouseholdIngredient.family_id == family_id,
            HouseholdIngredient.is_valid == INGREDIENT_IS_VALID,
        )
        items = list(self.db.scalars(stmt))
        for item in items:
            item.is_valid = INGREDIENT_INVALID
        self.db.commit()
        return len(items)