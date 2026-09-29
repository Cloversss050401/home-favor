"""营养计算服务：核心营养逻辑，本地二次校验防模型幻觉。

对齐硬性业务规则第 2、5 条：
- 缺口占比 = (DRIs每日推荐值 − 实际摄入)/DRIs每日推荐 ×100%；仅实际摄入<推荐值才算缺口
- 核心营养素 6 项：蛋白质、钙、铁、锌、维生素A、维生素C
- 以 MySQL 食物成分表 + DRIs 为唯一权威数据源，不信任模型数值
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from src.config.constants import CORE_NUTRIENTS, NUTRIENT_LABEL_CN
from src.models.dris_model import DrisStandard
from src.repository.dris_repo import DrisRepo
from src.repository.family_repo import FamilyRepo
from src.repository.food_nutrition_repo import FoodNutritionRepo
from src.repository.member_repo import MemberRepo
from src.schemas.recipe_schema import MemberAllocation


def _d2(value) -> Decimal:
    return Decimal(str(value or 0))


def _round(value: Decimal, ndigits: int = 2) -> Decimal:
    return value.quantize(Decimal("1." + "0" * ndigits), rounding=ROUND_HALF_UP)


class NutritionService:
    """营养计算服务（依赖注入 DB Session）。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.food_repo = FoodNutritionRepo(db)
        self.dris_repo = DrisRepo(db)
        self.member_repo = MemberRepo(db)
        self.family_repo = FamilyRepo(db)

    # ---------- 基础查表 ----------
    def food_nutrition(self, food_name: str) -> dict[str, Decimal] | None:
        """返回食材每 100g 的营养字典（核心 6 项），未知食材返回 None。"""
        row = self.food_repo.get_by_name(food_name)
        if row is None:
            return None
        return {nut: _d2(getattr(row, nut)) for nut in CORE_NUTRIENTS}

    def dris_value(self, target_type: str, nutrient: str) -> Decimal | None:
        row: DrisStandard | None = self.dris_repo.get(target_type, nutrient)
        return _d2(row.rni_value) if row else None

    def daily_rni(self, member, nutrient: str) -> Decimal | None:
        """按成员饮食目标推算 DRIs 人群类别，返回该成员某营养素每日推荐值。"""
        target = self._target_type(member)
        return self.dris_value(target, nutrient)

    @staticmethod
    def _target_type(member) -> str:
        """成员 -> DRIs target_type：
        婴幼儿辅食 -> baby；孕妈 -> pregnant；老年 -> elderly；
        减脂/增肌等其他 -> 按性别 adult_male/adult_female。
        """
        goal = getattr(member, "diet_goal", "normal")
        if goal == "baby":
            return "baby_6_12m"
        if goal == "pregnant":
            return "pregnant"
        if goal == "elderly":
            return "elderly"
        gender = getattr(member, "gender", "female")
        return "adult_male" if gender == "male" else "adult_female"

    # ---------- 分量换算 ----------
    def intake_from_amount(
        self, food_name: str, amount_g: Decimal
    ) -> dict[str, Decimal]:
        """根据食物成分表（每 100g）计算指定食用分量的营养素摄入。

        未知食材返回全 0（由调用方决定是否跳过）。
        """
        per100 = self.food_nutrition(food_name)
        if per100 is None:
            return {nut: Decimal("0") for nut in CORE_NUTRIENTS}
        ratio = _d2(amount_g) / Decimal("100")
        return {nut: _round(_d2(v) * ratio) for nut, v in per100.items()}

    # ---------- 缺口计算 ----------
    def gap_ratio(self, rni: Decimal, actual: Decimal) -> Decimal:
        """缺口占比 = (RNI - 实际)/RNI ×100%；仅实际<推荐值才算缺口，否则为 0。"""
        if rni <= 0:
            return Decimal("0")
        if actual >= rni:
            return Decimal("0")
        return _round((rni - actual) / rni * Decimal("100"), 2)

    def member_gap(
        self, member, intake: dict[str, Decimal]
    ) -> list[dict]:
        """计算某成员的核心营养素缺口清单。”

        返回：[{nutrient, nutrient_name, rni, actual, gap_ratio, status}]
        status: ok(达标) / gap(缺口>0) / big_gap(缺口>30%)
        """
        result = []
        for nutrient in CORE_NUTRIENTS:
            rni = self.daily_rni(member, nutrient)
            if rni is None:
                continue
            actual = _d2(intake.get(nutrient, 0))
            ratio = self.gap_ratio(rni, actual)
            if ratio > 0:
                status = "big_gap" if ratio > 30 else "gap"
            else:
                status = "ok"
            result.append(
                {
                    "nutrient": nutrient,
                    "nutrient_name": NUTRIENT_LABEL_CN.get(nutrient, nutrient),
                    "rni": rni,
                    "actual": actual,
                    "gap_ratio": ratio,
                    "status": status,
                }
            )
        return result

    def any_big_gap(self, gaps: list[dict]) -> bool:
        """是否任意核心营养素缺口 > 30%（触发采购条件之一）。"""
        return any(g["status"] == "big_gap" for g in gaps)

    # ---------- 本地二次校验（修正模型输出） ----------
    def local_verify_allocation(
        self, member, allocation: dict
    ) -> dict:
        """用食物成分表重算成员各菜品实际摄入，覆盖模型提供的缺口/摄入值。

        仅在本地数据可查时修正；本地查不到对应食材的项保持模型原值。
        """
        total_intake: dict[str, Decimal] = {}
        for dish in allocation.get("dishes", []):
            dish_name = dish.get("dish_name", dish.get("name", ""))
            amount = _d2(dish.get("amount_g", 0))
            if dish_name and amount > 0:
                intake = self.intake_from_amount(dish_name, amount)
                for nut, val in intake.items():
                    total_intake[nut] = total_intake.get(nut, Decimal("0")) + val

        gaps = self.member_gap(member, total_intake)
        # 仅有本地识别到任何食材数据时才覆写
        if any(v > 0 for v in total_intake.values()):
            allocation["nutrition_gap"] = [
                {
                    "nutrient": g["nutrient"],
                    "nutrient_name": g["nutrient_name"],
                    "rni": g["rni"],
                    "actual": g["actual"],
                    "gap_ratio": g["gap_ratio"],
                    "status": g["status"],
                }
                for g in gaps
            ]
        return allocation

    # ---------- 周报折算 ----------
    def decompose_dish(
        self, dish_name: str, amount_g: Decimal, recipe_record=None
    ) -> dict[str, Decimal]:
        """把一道菜拆解为原始食材营养合计。

        - 优先：关联食谱记录中该菜品的 main_ingredients 配比（等比例缩放）
        - 降级：菜品名直接作为食材查食物成分表（如仅含单一主食材）。
        """
        total: dict[str, Decimal] = {}
        if recipe_record is not None:
            for dish in recipe_record.shared_dishes or []:
                if dish.get("name") == dish_name:
                    ingredients = dish.get("main_ingredients", [])
                    if ingredients:
                        per = _d2(amount_g) / Decimal(len(ingredients))
                        for ing in ingredients:
                            intake = self.intake_from_amount(ing, per)
                            for nut, val in intake.items():
                                total[nut] = total.get(nut, Decimal("0")) + val
                        return {k: _round(v) for k, v in total.items()}
        # 降级：按单个食材处理
        return self.intake_from_amount(dish_name, amount_g)

    def summarize_nutrients(self, intakes: list[dict[str, Decimal]]) -> dict[str, Decimal]:
        """多餐/多天营养累加。"""
        total: dict[str, Decimal] = {}
        for intake in intakes:
            for nut, val in intake.items():
                total[nut] = total.get(nut, Decimal("0")) + _d2(val)
        return {k: _round(v) for k, v in total.items()}


def build_member_allocation(
    member_id: int, member_name: str, dishes: list[dict]
) -> MemberAllocation:
    """构造 MemberAllocation schema（供 recipe_service 使用）。"""
    return MemberAllocation(member_id=member_id, member_name=member_name, dishes=dishes)


def today() -> date:
    return date.today()