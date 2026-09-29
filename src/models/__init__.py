"""ORM 模型注册中心：统一导出 Base 与全部表模型。

用途：
1. `Base` 供各模型继承；
2. 聚合导入保证 `Base.metadata.create_all()` 能建出全部表；
3. 业务层可通过 `from src.models import FamilyMember` 引入模型。
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """项目 ORM 基类。"""


from src.models.family_model import Family  # noqa: E402,F401
from src.models.member_model import FamilyMember  # noqa: E402,F401
from src.models.ingredient_model import HouseholdIngredient  # noqa: E402,F401
from src.models.recipe_record_model import RecipeGenerationRecord  # noqa: E402,F401
from src.models.feedback_model import UserFeedback  # noqa: E402,F401
from src.models.report_model import WeeklyNutReport  # noqa: E402,F401
from src.models.food_nutrition_model import FoodNutrition  # noqa: E402,F401
from src.models.dris_model import DrisStandard  # noqa: E402,F401

__all__ = [
    "Base",
    "Family",
    "FamilyMember",
    "HouseholdIngredient",
    "RecipeGenerationRecord",
    "UserFeedback",
    "WeeklyNutReport",
    "FoodNutrition",
    "DrisStandard",
]