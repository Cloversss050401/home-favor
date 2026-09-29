"""营养计算服务：核心营养逻辑，本地二次校验防模型幻觉。

对齐硬性业务规则第 2、5 条：
- 缺口占比 = (DRIs每日推荐值 − 实际摄入)/DRIs每日推荐 ×100%；仅实际摄入<推荐值才算缺口
- 核心营养素 6 项：蛋白质、钙、铁、锌、维生素A、维生素C
- 以 MySQL 食物成分表 + DRIs 为唯一权威数据源，不信任模型数值
"""
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVITY_PAL,
    CORE_NUTRIENTS,
    DIET_GOAL_ENERGY_FACTOR,
    GAP_ADVICE_CN,
    NUTRIENT_LABEL_CN,
    PREGNANT_ENERGY_ADD_KCAL,
)
from app.modules.nutrition.models import DrisStandard
from app.modules.nutrition.repository import DrisRepo
from app.modules.family_member.repository import FamilyRepo
from app.modules.nutrition.repository import FoodNutritionRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.recipe.schemas import MemberAllocation


def _d2(value) -> Decimal:
    return Decimal(str(value or 0))


def _round(value: Decimal, ndigits: int = 2) -> Decimal:
    return value.quantize(Decimal("1." + "0" * ndigits), rounding=ROUND_HALF_UP)


# ---------- 缺口建议：按人分套的食材清单（成分表内可反算量） ----------
ANIMAL_CATEGORIES = {"禽肉", "畜肉", "水产"}  # 素食排除
BABY_UNSAFE_CATEGORIES = {"禽肉", "畜肉", "水产"}  # 婴幼儿难消化排除

GAP_FOODS_GENERAL = {
    "protein": ["鸡胸肉", "鸡蛋", "豆腐", "牛奶"],
    "calcium": ["牛奶", "豆腐", "油菜", "西兰花"],
    "iron": ["牛肉", "菠菜", "鸡蛋", "豆腐"],
    "zinc": ["牛肉", "鸡蛋", "豆腐", "大米"],
    "vitamin_a": ["胡萝卜", "菠菜", "西兰花"],
    "vitamin_c": ["西兰花", "油菜", "番茄", "土豆"],
}
GAP_FOODS_VEGETARIAN = {
    "protein": ["豆腐", "鸡蛋", "牛奶", "面粉"],
    "calcium": ["豆腐", "牛奶", "油菜", "菠菜"],
    "iron": ["菠菜", "豆腐", "油菜", "鸡蛋"],
    "zinc": ["豆腐", "鸡蛋", "大米", "面粉"],
    "vitamin_a": ["胡萝卜", "菠菜", "西兰花"],
    "vitamin_c": ["西兰花", "油菜", "番茄"],
}
GAP_FOODS_BABY = {
    "protein": ["鸡蛋", "豆腐", "牛奶", "面粉"],
    "calcium": ["牛奶", "豆腐", "油菜", "西兰花"],
    "iron": ["鸡蛋", "菠菜", "豆腐", "油菜"],
    "zinc": ["鸡蛋", "豆腐", "牛奶", "大米"],
    "vitamin_a": ["胡萝卜", "菠菜", "西兰花"],
    "vitamin_c": ["西兰花", "油菜", "番茄"],
}

# 过敏原代码 → 中文食材关键词（子串匹配食材名/类别）
ALLERGEN_CODE_CN = {
    "shellfish": "虾",
    "soy": "豆腐",
    "fish": "鱼",
    "egg": "鸡蛋",
    "milk": "牛奶",
    "nuts": "坚果",
    "peanut": "花生",
    "wheat": "面",
    "spicy": "辣",
}


def _norm_food(s: str) -> str:
    """食材名简单归一：去空白。"""
    return re.sub(r"\s+", "", s or "")


def _is_vegetarian(member) -> bool:
    """素食判定：目标=素食，或特征/附加需求含素食关键词。"""
    if getattr(member, "diet_goal", "") == "vegetarian":
        return True
    vals = [
        str(getattr(member, "traits", None) or []),
        str(getattr(member, "dietary_needs", None) or []),
    ]
    blob = "".join(vals).lower()
    return "vegetarian" in blob or "素食" in blob


def _is_baby(member) -> bool:
    """婴幼儿判定：角色=baby 或年龄<3 岁。"""
    if getattr(member, "role", "") == "baby":
        return True
    try:
        return int(member.age or 0) < 3
    except (TypeError, ValueError):
        return False


def gap_foods_for(member, nutrient: str) -> list[str]:
    """按成员类型取该营养素可补的食材顺序（宝宝→素食→通用）。"""
    if _is_baby(member):
        return list(GAP_FOODS_BABY.get(nutrient, []))
    if _is_vegetarian(member):
        return list(GAP_FOODS_VEGETARIAN.get(nutrient, []))
    return list(GAP_FOODS_GENERAL.get(nutrient, []))


def _exclude_terms(member) -> set[str]:
    """收集该成员需要排除的食材关键词（过敏原 + 忌口文本）。"""
    terms: set[str] = set()
    for a in getattr(member, "allergens", None) or []:
        a = str(a).strip()
        if not a or a in ("无", "none", "None"):
            continue
        terms.add(a)
        code = a.lower()
        if code in ALLERGEN_CODE_CN:
            terms.add(ALLERGEN_CODE_CN[code])
    for txt in list(getattr(member, "dietary_restrictions", None) or []) + [
        getattr(member, "avoid", "") or ""
    ]:
        txt = str(txt).strip()
        if not txt or txt in ("无", "none", "None"):
            continue
        if txt.startswith("不吃") and len(txt) > 2:
            terms.add(txt[2:].strip())
        else:
            terms.add(txt)
    return terms


class NutritionService:
    """营养计算服务（依赖注入 DB Session）。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.food_repo = FoodNutritionRepo(db)
        self.dris_repo = DrisRepo(db)
        self.member_repo = MemberRepo(db)
        self.family_repo = FamilyRepo(db)

    # ---------- 基础查表 ----------
    NUTRIENT_CODES: tuple[str, ...] = CORE_NUTRIENTS + ("energy",)  # 含能量

    def food_nutrition(self, food_name: str) -> dict[str, Decimal] | None:
        """返回食材每 100g 的营养字典（核心 6 项 + 能量），未知食材返回 None。"""
        row = self.food_repo.get_by_name(food_name)
        if row is None:
            return None
        out = {nut: _d2(getattr(row, nut)) for nut in CORE_NUTRIENTS}
        out["energy"] = _d2(getattr(row, "energy", 0))
        return out

    def dris_value(self, target_type: str, nutrient: str) -> Decimal | None:
        row: DrisStandard | None = self.dris_repo.get(target_type, nutrient)
        return _d2(row.rni_value) if row else None

    def daily_rni(self, member, nutrient: str) -> Decimal | None:
        """按成员饮食目标推算 DRIs 人群类别，返回该成员某营养素每日推荐值。"""
        target = self._target_type(member)
        return self.dris_value(target, nutrient)

    @staticmethod
    def _target_type(member) -> str:
        """成员 -> DRIs target_type：按年龄分段 + 特殊人群优先。

        - 孕妈 -> pregnant（优先）
        - 年龄分档：<3 婴幼儿 / 3-6 儿童 / 7-12 儿童 / 13-17 青少年（分性别）/
          18-64 成人（分性别，50+ 用 50_64 档）/ >=65 老年
        """
        goal = getattr(member, "diet_goal", "normal")
        if goal == "pregnant":
            return "pregnant"
        gender = getattr(member, "gender", "female")
        age = float(getattr(member, "age", 0) or 0)
        if age < 3:
            return "baby_6_12m"
        if age < 7:
            return "child_3_6"
        if age < 13:
            return "child_7_12"
        if age < 18:
            return "teen_male" if gender == "male" else "teen_female"
        if age < 65:
            return (
                "adult_male" if gender == "male" else "adult_female"
            ) if age < 50 else (
                "adult_male_50_64" if gender == "male" else "adult_female_50_64"
            )
        return "elderly"

    # ---------- 每日能量 / 蛋白质（分龄尺子） ----------
    @staticmethod
    def _energy_by_age(age: float, gender: str) -> Decimal:
        """无身高体重时的能量查表兜底（千卡/天，示例值需按指南核对）。"""
        table = [
            (3, 900.0),          # 婴幼儿
            (7, 1300.0),         # 3-6 岁
            (13, 1800.0),        # 7-12 岁
            (18, 2500.0 if gender == "male" else 2200.0),  # 青少年
            (50, 2400.0 if gender == "male" else 2000.0),  # 成人
            (65, 2100.0 if gender == "male" else 1800.0),  # 50-64
            (999, 2000.0 if gender == "male" else 1700.0),  # 老年
        ]
        for bound, kcal in table:
            if age < bound:
                return Decimal(str(kcal))
        return Decimal("2000")

    def daily_energy_kcal(self, member) -> Decimal:
        """成员每日能量目标（千卡）。

        - 填了身高体重：Mifflin-St Jeor 基础代谢 × 活动系数（PAL）
        - 未填：按年龄/性别查表兜底
        - 再叠加目标系数（增肌×1.15 / 减脂×0.85 / 孕期+300）
        """
        age = float(getattr(member, "age", 0) or 0)
        gender = getattr(member, "gender", "female")
        goal = getattr(member, "diet_goal", "normal")
        height = getattr(member, "height_cm", None)
        weight = getattr(member, "weight_kg", None)

        if height and weight:
            bmr = (
                Decimal("10") * _d2(weight)
                + Decimal("6.25") * _d2(height)
                - Decimal("5") * Decimal(str(age))
                + (Decimal("5") if gender == "male" else Decimal("-161"))
            )
            pal = Decimal(str(ACTIVITY_PAL.get(getattr(member, "activity", "light"), 1.375)))
            base = bmr * pal
        else:
            base = self._energy_by_age(age, gender)

        factor = Decimal(str(DIET_GOAL_ENERGY_FACTOR.get(goal, 1.0)))
        base = base * factor
        if goal == "pregnant":
            base += Decimal(str(PREGNANT_ENERGY_ADD_KCAL))
        return _round(base, 0)

    def daily_protein_g(self, member) -> Decimal:
        """成员每日蛋白质目标（克）。

        - 有体重：增肌 1.6-2.2g/kg（取 1.8）、老人 1.1g/kg、普通成人 0.9g/kg
        - 无体重：按年龄/性别查表
        """
        goal = getattr(member, "diet_goal", "normal")
        age = float(getattr(member, "age", 0) or 0)
        gender = getattr(member, "gender", "female")
        weight = getattr(member, "weight_kg", None)
        if weight:
            if goal == "muscle":
                per = Decimal("1.8")
            elif age >= 65:
                per = Decimal("1.1")
            else:
                per = Decimal("0.9")
            return _round(_d2(weight) * per, 0)
        if age < 3:
            return Decimal("20")
        if age < 7:
            return Decimal("30")
        if age < 13:
            return Decimal("40")
        if age < 18:
            return Decimal("75" if gender == "male" else "60")
        if age < 65:
            return Decimal("65" if gender == "male" else "55")
        return Decimal("60")

    def member_targets(self, member) -> dict[str, Decimal | None]:
        """成员尺子包：{energy_kcal, protein_g, 6 项 RNI}，供 Prompt / 校验使用。"""
        targets: dict[str, Decimal | None] = {
            "energy_kcal": self.daily_energy_kcal(member),
            "protein_g": self.daily_protein_g(member),
        }
        for nutrient in CORE_NUTRIENTS:
            targets[nutrient] = self.daily_rni(member, nutrient)
        return targets

    # ---------- 分量换算 ----------
    def intake_from_amount(
        self, food_name: str, amount_g: Decimal
    ) -> dict[str, Decimal]:
        """根据食物成分表（每 100g）计算指定食用分量的营养素摄入（含能量）。

        未知食材返回全 0（由调用方决定是否跳过）。
        """
        per100 = self.food_nutrition(food_name)
        if per100 is None:
            return {nut: Decimal("0") for nut in self.NUTRIENT_CODES}
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

    def build_gap_advice(
        self, member, nutrient: str, gap_amount: Decimal
    ) -> list[str]:
        """按人/按量/按库存生成具体补营养建议。

        返回如 ['鸡蛋 1 个（家里有）', '牛奶 300ml（约 1 杯，需采购）']：
        - 按人：素食→植物源+蛋奶；宝宝→软烂安全（无肉/水产）；过敏与忌口剔除；
        - 按量：缺口量 ÷ 每 100g 含量反算克数，单项设上限，最多 3 项；
        - 按库存：家里有的标“家里有”，没有的标“需采购”。
        """
        if gap_amount <= 0:
            return []
        home = self._home_food_names(member)
        exclude = _exclude_terms(member)
        candidates: list[tuple[float, str, str]] = []
        for food in gap_foods_for(member, nutrient):
            per100 = self.food_nutrition(food)
            if not per100:
                continue
            val = float(_d2(per100.get(nutrient, 0)))
            if val <= 0:
                continue
            if any(t in food for t in exclude):
                continue
            row = self.food_repo.get_by_name(food)
            cat = (row.food_category if row else "") or ""
            if any(t in cat for t in exclude):
                continue
            candidates.append((val, food, cat))
        if not candidates:
            return []

        remain = float(gap_amount)
        advice: list[str] = []
        for val, food, cat in candidates:
            cap = 500 if food == "牛奶" else (110 if food == "鸡蛋" else 200)
            if _is_baby(member):
                cap = 300 if food == "牛奶" else (50 if food == "鸡蛋" else 100)
            need = min(remain / val * 100, cap)
            if need < 20:
                continue
            need = self._round_amount(food, need)
            if need <= 0:
                continue
            stock = "家里有" if _norm_food(food) in home else "需采购"
            advice.append(f"{food} {self._amount_text(food, need)}（{stock}）")
            remain -= need / 100 * val
            if len(advice) >= 3 or remain <= 0:
                break
        return advice

    @staticmethod
    def _round_amount(food: str, need: float) -> float:
        """建议量取整：牛奶 50ml、鸡蛋 1 个（50g）、其他 10g。"""
        if food == "牛奶":
            return max(round(need / 50) * 50, 50)
        if food == "鸡蛋":
            return max(round(need / 50) * 50, 50)
        return max(round(need / 10) * 10, 20)

    @staticmethod
    def _amount_text(food: str, grams: float) -> str:
        """克数 → 可读量词：牛奶 ml/杯、鸡蛋 个、其他 g。"""
        g = int(round(grams))
        if food == "牛奶":
            cups = g / 250
            if abs(cups - round(cups)) < 0.05 and cups >= 1:
                return f"{g}ml（约{int(round(cups))}杯）"
            return f"{g}ml（约{cups:.1f}杯）" if g >= 250 else f"{g}ml"
        if food == "鸡蛋":
            n = max(round(g / 50), 1)
            return f"{n} 个"
        return f"{g}g"

    def _home_food_names(self, member) -> set[str]:
        """该成员家庭当前有效的食材名集合（用于库存标注）。"""
        try:
            from app.modules.ingredient.repository import IngredientRepo

            repo = IngredientRepo(self.db)
            return {
                _norm_food(ing.name)
                for ing in repo.list_valid(member.family_id)
            }
        except Exception:
            return set()

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
                    "advice": (
                        self.build_gap_advice(member, nutrient, _d2(rni) - actual)
                        if ratio > 0
                        else []
                    ),
                }
            )
        return result

    def any_big_gap(self, gaps: list[dict]) -> bool:
        """是否任意核心营养素缺口 > 30%（触发采购条件之一）。"""
        return any(g["status"] == "big_gap" for g in gaps)

    # ---------- 本地二次校验（修正模型输出） ----------
    def local_verify_allocation(
        self, member, allocation: dict, shared_dishes: list | None = None
    ) -> dict:
        """用食物成分表重算成员各菜品实际摄入，覆盖模型提供的缺口/摄入值。

        按菜谱主料等比例拆解查询（不拿菜名直接查）：菜谱记录里有 main_ingredients
        时按主料折算；查不到主料的菜按菜名直接查。
        全部食材都查不到时保持模型原值（缺口不可信，调用方应提示）。
        """
        dish_map: dict[str, list[str]] = {}
        for d in shared_dishes or []:
            name = getattr(d, "name", None) or (d.get("name") if isinstance(d, dict) else None)
            ings = getattr(d, "main_ingredients", None) or (d.get("main_ingredients") if isinstance(d, dict) else None)
            if name:
                dish_map[str(name)] = [str(x) for x in (ings or [])]

        total_intake: dict[str, Decimal] = {}
        for dish in allocation.get("dishes", []):
            dish_name = dish.get("dish_name", dish.get("name", ""))
            amount = _d2(dish.get("amount_g", 0))
            if not dish_name or amount <= 0:
                continue
            ingredients = dish_map.get(str(dish_name), [])
            if ingredients:
                per = amount / Decimal(len(ingredients))
                for ing in ingredients:
                    intake = self.intake_from_amount(ing, per)
                    for nut, val in intake.items():
                        total_intake[nut] = total_intake.get(nut, Decimal("0")) + val
            else:
                intake = self.intake_from_amount(dish_name, amount)
                for nut, val in intake.items():
                    total_intake[nut] = total_intake.get(nut, Decimal("0")) + val

        gaps = self.member_gap(member, total_intake)
        # 仅有本地识别到任何食材数据时才覆写（值转 float 保证 JSON 可序列化）
        if any(v > 0 for v in total_intake.values()):
            allocation["nutrition_gap"] = [
                {
                    "nutrient": g["nutrient"],
                    "nutrient_name": g["nutrient_name"],
                    "rni": float(g["rni"]),
                    "actual": float(g["actual"]),
                    "gap_ratio": float(g["gap_ratio"]),
                    "status": g["status"],
                    "advice": list(g["advice"]),
                }
                for g in gaps
            ]
        return allocation

    # ---------- 周报折算 ----------
    def decompose_dish(
        self, dish_name: str, amount_g: Decimal, recipe_record=None,
        custom_ingredients: list | None = None,
    ) -> dict[str, Decimal]:
        """把一道菜拆解为原始食材营养合计（含能量）。

        - 优先：自定义菜品主料（custom_ingredients，方案外自做菜）
        - 其次：关联食谱记录中该菜品的 main_ingredients 配比（等比例缩放）
        - 降级：菜品名直接作为食材查食物成分表（如仅含单一主食材）。
        """
        total: dict[str, Decimal] = {}
        ingredients: list[str] | None = None
        if custom_ingredients:
            ingredients = [str(x) for x in custom_ingredients if str(x).strip()]
        elif recipe_record is not None:
            for dish in recipe_record.shared_dishes or []:
                if dish.get("name") == dish_name:
                    ingredients = dish.get("main_ingredients", [])
                    break
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



from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import DISH_SERVING_BASE_G
from app.core.exceptions import RecipeRecordNotFound
from app.modules.nutrition.models import UserFeedback
from app.modules.nutrition.repository import FeedbackRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.recipe.repository import RecipeRecordRepo
from app.modules.nutrition.schemas import FeedbackCreate, FeedbackItem


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback_repo = FeedbackRepo(db)
        self.member_repo = MemberRepo(db)
        self.record_repo = RecipeRecordRepo(db)

    @staticmethod
    def _dish_total_g(record, dish_name: str) -> Decimal:
        """该道菜整份参考量：优先记录中估计份量×基准，缺失按 1 份基准兜底。"""
        if record is not None:
            for dish in record.shared_dishes or []:
                if dish.get("name") == dish_name:
                    servings = int(dish.get("estimated_servings", 1) or 1)
                    return Decimal(str(servings)) * Decimal(str(DISH_SERVING_BASE_G))
        return Decimal(str(DISH_SERVING_BASE_G))

    def create_feedback(self, payload: FeedbackCreate) -> int:
        """存储反馈明细。

        - 手动输入 item（amount_g/ratio 有值）优先级更高，直接存储；
          仅给 ratio 时按整道菜参考量折算 amount_g 落库；
        - use_ai_amount=True 时，从关联记录（缺失则最新记录）按成员复制 AI 推荐分量。
        """
        record = None
        ai_map: dict[int, list[tuple[str, Decimal]]] = {}
        if payload.recipe_record_id:
            record = self.record_repo.get(payload.recipe_record_id)
            if record is None:
                raise RecipeRecordNotFound()
        elif payload.use_ai_amount:
            record = self.record_repo.latest(payload.family_id)
            if record is None:
                raise RecipeRecordNotFound()

        if record is not None:
            for alloc in record.member_allocation or []:
                mid = int(alloc.get("member_id", 0))
                dishes = [
                    (
                        str(d.get("dish_name", "")),
                        Decimal(str(d.get("amount_g", 0) or 0)),
                    )
                    for d in alloc.get("dishes", []) or []
                    if d.get("dish_name")
                ]
                ai_map[mid] = dishes

        manual: dict[int, list[tuple[str, Decimal]]] = {}
        for it in payload.items:
            if it.amount_g is None and it.ratio is None:
                continue  # 手动输入项必须带分量或比例
            amount = it.amount_g
            if amount is None and it.ratio is not None:
                amount = self._dish_total_g(record, it.dish_name) * it.ratio
            manual.setdefault(it.member_id, []).append((it.dish_name, amount))

        rows: list[UserFeedback] = []
        valid_members = {m.id for m in self.member_repo.list_active(payload.family_id)}
        for item in payload.items:
            if item.member_id not in valid_members:
                continue
            # 手动输入优先；否则一键全选回填
            dish_name = item.dish_name
            amount: Decimal | None = item.amount_g
            is_ai = 0
            if amount is None and item.ratio is not None:
                amount = self._dish_total_g(record, dish_name) * item.ratio
            if amount is None:
                ai_dishes = ai_map.get(item.member_id, [])
                matched = next((x for x in ai_dishes if x[0] == dish_name), None)
                if matched is not None:
                    amount = matched[1]
                    is_ai = 1
                else:
                    continue  # 找不到 AI 分量则跳过该条
            rows.append(
                UserFeedback(
                    family_id=payload.family_id,
                    recipe_record_id=record.id if record else None,
                    member_id=item.member_id,
                    dish_name=dish_name,
                    amount_g=amount,
                    eaten_date=payload.eaten_date,
                    meal_type=payload.meal_type or "",
                    custom_ingredients=item.custom_ingredients or None,
                    is_ai_recommended=is_ai,
                )
            )
        if not rows:
            raise ValueError("无有效反馈条目：请检查成员与分量")
        return self.feedback_repo.create_many(rows)

    def list_feedback(
        self, family_id: int, start: date, end: date
    ) -> list[UserFeedback]:
        """按日期范围查询反馈列表。"""
        return self.feedback_repo.list_by_range(family_id, start, end)



from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import (
    CORE_NUTRIENTS,
    EXCEED_RATIO,
    GAP_ADVICE_CN,
    GAP_CONSECUTIVE_DAYS,
    NUTRIENT_LABEL_CN,
    WEEK_REPORT_MIN_ACTUAL_DAYS,
)
from app.core.exceptions import ReportNotReady
from app.modules.nutrition.models import UserFeedback
from app.modules.nutrition.models import WeeklyNutReport
from app.modules.nutrition.repository import FeedbackRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.nutrition.repository import ReportRepo
from app.modules.recipe.repository import RecipeRecordRepo
from app.common.utils import date_list


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback_repo = FeedbackRepo(db)
        self.member_repo = MemberRepo(db)
        self.record_repo = RecipeRecordRepo(db)
        self.report_repo = ReportRepo(db)
        self.nutrition = NutritionService(db)

    # ---------- 聚合计算 ----------
    def _feedback_intake_by_meal(
        self, feedback_rows: list[UserFeedback], member_id: int
    ) -> dict[tuple[date, str], dict[str, dict[str, Decimal]]]:
        """按 (日期, 餐次) 分档统计成员摄入。

        返回 {(date, meal): {"actual": {nut: val}, "ai_est": {nut: val}}}
        actual=手动实际值（最真实）；ai_est=一键全选复用的 AI 推荐分量（估算）。
        """
        per_meal: dict[tuple[date, str], dict[str, dict[str, Decimal]]] = {}
        for row in feedback_rows:
            if row.member_id != member_id:
                continue
            record = (
                self.record_repo.get(row.recipe_record_id)
                if row.recipe_record_id
                else None
            )
            intake = self.nutrition.decompose_dish(
                row.dish_name, row.amount_g, record, row.custom_ingredients
            )
            key = (row.eaten_date, row.meal_type or "")
            slot = per_meal.setdefault(
                key, {"actual": {}, "ai_est": {}}
            )
            bucket = slot["actual" if row.is_ai_recommended == 0 else "ai_est"]
            for nut, val in intake.items():
                bucket[nut] = bucket.get(nut, Decimal("0")) + Decimal(str(val))
        return per_meal

    def _last_recipe_estimate(
        self, family_id: int, member_id: int, day: date, meal_type: str
    ) -> dict[str, Decimal] | None:
        """无反馈的餐次：默认按该餐次当天最后一次生成的食谱估算。

        取当天 meal_type 匹配（或未限定餐次）中 id 最大的一条记录，
        返回该成员 AI 推荐分量的摄入合计；当天没有可匹配食谱返回 None。
        """
        records = self.record_repo.list_by_family(family_id, limit=200)
        for rec in records:
            created = getattr(rec, "created_at", None)
            rec_day = created.date() if created else None
            if rec_day != day:
                continue
            rec_meal = getattr(rec, "meal_type", "") or ""
            if rec_meal not in ("", meal_type):
                continue
            for alloc in rec.member_allocation or []:
                if int(alloc.get("member_id", 0)) != member_id:
                    continue
                total: dict[str, Decimal] = {}
                for d in alloc.get("dishes", []) or []:
                    dish_name = str(d.get("dish_name", ""))
                    amount = _d2(d.get("amount_g", 0))
                    if not dish_name or amount <= 0:
                        continue
                    intake = self.nutrition.decompose_dish(dish_name, amount, rec)
                    for nut, val in intake.items():
                        total[nut] = total.get(nut, Decimal("0")) + Decimal(str(val))
                return {k: _round(v) for k, v in total.items()}
        return None

    @staticmethod
    def _blend_meal(slot: dict[str, dict[str, Decimal]]) -> dict[str, Decimal]:
        """餐次混合口径：实际优先，估算（AI 预填）补缺。"""
        merged: dict[str, Decimal] = dict(slot["actual"])
        for nut, val in slot["ai_est"].items():
            if nut not in merged:
                merged[nut] = val
        return merged

    def _member_daily_breakdown(
        self, family_id: int, member, feedback_rows: list[UserFeedback],
        days: list[date],
    ) -> tuple[dict[date, dict[str, Decimal]], dict[date, str]]:
        """成员逐日摄入 + 每日来源口径。

        返回 (daily_full, daily_source)：
        - daily_full[day] = 混合口径营养摄入（actual 优先 + 估算补缺 + 无反馈餐次按最后食谱估算）
        - daily_source[day] = "actual" | "est" | "mixed"
        """
        per_meal = self._feedback_intake_by_meal(feedback_rows, member.id)
        daily_full: dict[date, dict[str, Decimal]] = {}
        daily_source: dict[date, str] = {}

        # 先按日期聚合反馈（分档）
        day_buckets: dict[date, dict[str, dict[str, Decimal]]] = {}
        for (day, _meal), slot in per_meal.items():
            bucket = day_buckets.setdefault(day, {"actual": {}, "ai_est": {}})
            for src in ("actual", "ai_est"):
                for nut, val in slot[src].items():
                    bucket[src][nut] = bucket[src].get(nut, Decimal("0")) + val

        # 每个餐次：有反馈用反馈（混合），无反馈按该餐次最后一次食谱估算
        from app.core.constants import MEAL_TYPE_ENUM

        for day in days:
            day_total: dict[str, Decimal] = {}
            day_source = "no_data"
            for meal in MEAL_TYPE_ENUM:
                slot = per_meal.get((day, meal)) or per_meal.get((day, ""))
                if slot is not None:
                    merged = self._blend_meal(slot)
                    for nut, val in merged.items():
                        day_total[nut] = day_total.get(nut, Decimal("0")) + val
                    if slot["actual"]:
                        day_source = "actual" if day_source != "actual" else day_source
                        if day_source in ("no_data", "est"):
                            day_source = "actual"
                else:
                    est = self._last_recipe_estimate(family_id, member.id, day, meal)
                    if est is not None:
                        for nut, val in est.items():
                            day_total[nut] = day_total.get(nut, Decimal("0")) + val
                        if day_source == "no_data":
                            day_source = "est"
            if day_total:
                daily_full[day] = day_total
                daily_source[day] = day_source if day_source != "no_data" else "est"
            else:
                daily_source[day] = "no_data"
        return daily_full, daily_source

    def _consecutive_gaps(
        self, member, daily_full: dict[date, dict[str, Decimal]],
        days: list[date], nutrient: str, rni: Decimal,
    ) -> int:
        """统计一周内该成员该营养素缺口>30% 的天数（混合口径）。"""
        count = 0
        for day in days:
            daily = daily_full.get(day)
            if daily is None:
                continue
            actual = _d2(daily.get(nutrient, 0))
            if self.nutrition.gap_ratio(rni, actual) > 30:
                count += 1
        return count

    def build_report(self, family_id: int, week_start: date, week_end: date) -> dict:
        """生成周报数据字典（不落库，由调用方决定落库）。

        口径：每人每天每餐——实际反馈 > AI 预填估算 > 该餐次最后一次食谱估算。
        报告标注 X 天实际 / Y 天估算；整周实际记录不足 3 天时提示结论仅供参考。
        """
        members = self.member_repo.list_active(family_id)
        feedback_rows = self.feedback_repo.list_by_range(
            family_id, week_start, week_end
        )
        if not feedback_rows:
            raise ReportNotReady()

        days = [d for d in date_list(week_start, week_end)]
        member_summaries = []
        all_tips: list[str] = []
        must_buy: list[dict] = []
        daily_full_all: dict[int, dict[date, dict[str, Decimal]]] = {}

        for member in members:
            daily_full, daily_source = self._member_daily_breakdown(
                family_id, member, feedback_rows, days
            )
            daily_full_all[member.id] = daily_full
            recorded_days = [d for d in days if daily_source[d] != "no_data"]
            if not recorded_days:
                continue
            actual_days = sum(1 for d in recorded_days if daily_source[d] == "actual")
            est_days = sum(1 for d in recorded_days if daily_source[d] != "actual")

            nutrients_summary = []
            # 能量行：成员每日能量目标（周报与蛋白质并列显示，体现一人一量）
            energy_rni = self.nutrition.daily_energy_kcal(member)
            if energy_rni:
                nutrients_summary.append(
                    self._nutrient_row("energy", "能量(千卡)", energy_rni,
                                       recorded_days, daily_full)
                )
            for nut in CORE_NUTRIENTS:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is None:
                    continue
                row = self._nutrient_row(nut, NUTRIENT_LABEL_CN.get(nut, nut),
                                         rni, recorded_days, daily_full)
                nutrients_summary.append(row)
                # 连续缺口检测：同成员同营养素缺口>30% 满 3 天 → 必买项
                gap_days = self._consecutive_gaps(member, daily_full, days, nut, rni)
                if gap_days >= GAP_CONSECUTIVE_DAYS:
                    foods = GAP_ADVICE_CN.get(nut, [])[:2]
                    for food in foods:
                        must_buy.append({
                            "food": food,
                            "member_id": member.id,
                            "member_name": member.name,
                            "nutrient": nut,
                            "nutrient_name": NUTRIENT_LABEL_CN.get(nut, nut),
                            "gap_days": gap_days,
                            "advice": foods,
                        })
                    all_tips.append(
                        f"{member.name}本周 {nut} 缺口超过 30% 累计 {gap_days} 天，"
                        f"建议采购：{'、'.join(foods)}，下周菜谱优先安排含这些食材的菜"
                    )

            problem = [
                f"{n['nutrient_name']}超标" for n in nutrients_summary if n["exceeded"]
            ] + [
                f"{n['nutrient_name']}摄入不足(达标率{n['rate']}%)"
                for n in nutrients_summary
                if not n["exceeded"] and n["rate"] < 100
            ]
            member_summaries.append(
                {
                    "member_id": member.id,
                    "member_name": member.name,
                    "nutrients": nutrients_summary,
                    "problem_summary": problem,
                    "stats": {
                        "actual_days": actual_days,
                        "est_days": est_days,
                        "no_data_days": sum(
                            1 for d in days if daily_source[d] == "no_data"
                        ),
                    },
                }
            )
            all_tips.extend(problem)

        if not member_summaries:
            raise ReportNotReady("本周无有效成员反馈记录，无法生成周报")

        # 家庭级有效天数：任一成员当天有数据即算一天
        all_recorded = {
            d for m in member_summaries
            for d in days
            if d in daily_full_all.get(m["member_id"], {})
        }
        family_effective = len(all_recorded)
        family_actual_days = max(
            (m["stats"]["actual_days"] for m in member_summaries), default=0
        )
        if family_actual_days < WEEK_REPORT_MIN_ACTUAL_DAYS:
            all_tips.insert(
                0,
                "本周多数为估算口径（AI 预填或按最后一次食谱推算），"
                "结论仅供参考；建议每餐在「做菜反馈」填写实际分量。",
            )

        # 按成员去重必须必买（同食材同成员只留一条）
        must_buy_dedup: dict[tuple, dict] = {}
        for item in must_buy:
            key = (item["food"], item["member_id"], item["nutrient"])
            if key not in must_buy_dedup or item["gap_days"] > must_buy_dedup[key]["gap_days"]:
                must_buy_dedup[key] = item
        must_buy_items = sorted(
            must_buy_dedup.values(),
            key=lambda x: (x["member_name"], x["nutrient_name"], x["food"]),
        )

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "effective_days": family_effective,
            "stats": {
                "effective_days": family_effective,
                "actual_days": family_actual_days,
                "est_days": family_effective - family_actual_days,
            },
            "members": member_summaries,
            "must_buy_items": must_buy_items,
            "weekly_tips": (
                self._tips(all_tips) or ["下周继续保持规律饮食与运动"]
            ),
        }

    def _nutrient_row(
        self, nut: str, name: str, rni: Decimal,
        recorded_days: list[date], daily_full: dict[date, dict[str, Decimal]],
    ) -> dict:
        """单个营养素行：总摄入/日均/达标率/超标/缺口。"""
        total = sum(
            (_d2(daily_full[d].get(nut, 0)) for d in recorded_days), Decimal("0")
        )
        daily_avg = total / Decimal(len(recorded_days))
        rate = (
            total / (rni * Decimal(len(recorded_days))) * Decimal("100")
            if rni and len(recorded_days)
            else Decimal("0")
        )
        exceeded = daily_avg > rni * Decimal(str(EXCEED_RATIO))
        gap = (rni - daily_avg) * Decimal(len(recorded_days))
        return {
            "nutrient_code": nut,
            "nutrient_name": name,
            "rni_per_day": float(rni),
            "effective_days": len(recorded_days),
            "total_intake": round(float(total), 2),
            "daily_avg": round(float(daily_avg), 2),
            "rate": round(float(rate), 2),
            "exceeded": exceeded,
            "gap": round(float(gap if gap > 0 else 0), 2),
        }

    @staticmethod
    def _tips(problems: list[str]) -> list[str]:
        """转成建议列表（去重，最多 6 条；连续缺口已生成具体采购建议）。"""
        seen = []
        for p in problems:
            if p not in seen:
                seen.append(p)
        return seen[:6]

    # ---------- 落库 ----------
    def save_report(
        self,
        family_id: int,
        week_start: date,
        week_end: date,
        report_data: dict,
        generate_type: int = 0,
    ) -> WeeklyNutReport:
        report = WeeklyNutReport(
            family_id=family_id,
            week_start=week_start,
            week_end=week_end,
            generate_type=generate_type,
            report_data=report_data,
        )
        return self.report_repo.create(report)

    def list_reports(self, family_id: int) -> list[WeeklyNutReport]:
        return self.report_repo.list_by_family(family_id)

    def get_report(self, report_id: int) -> WeeklyNutReport | None:
        return self.report_repo.get(report_id)

    def delete_report(self, report_id: int) -> bool:
        """删除一条周报记录（产物删除，不影响其他数据）。"""
        return self.report_repo.delete(report_id)
