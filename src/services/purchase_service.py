"""智能采购清单业务。

对齐硬性业务规则第 2 条：
- 触发条件：任意成员核心营养素缺口>30% 或 主菜<2 道
- 计算口径：满足全家 3 天需求；仅已录重量才扣减存量；扣减后≤0 移除
- 无重量食材：标记“家中已有”，不扣减
- 同义词合并同类食材；P0/P1/P2 排序；导出 Excel 字段固定
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from src.config.constants import (
    NUTRIENT_LABEL_CN,
    PURCHASE_DAYS,
    PURCHASE_P0,
    PURCHASE_P1,
    PURCHASE_P2,
    REMARK_ALREADY_ENOUGH,
    REMARK_HAS_NO_WEIGHT,
)
from src.repository.ingredient_repo import IngredientRepo
from src.repository.member_repo import MemberRepo
from src.repository.recipe_record_repo import RecipeRecordRepo
from src.schemas.recipe_schema import PurchaseItem, RecipeGenerateResult
from src.services.nutrition_service import NutritionService
from src.utils.excel_export import export_purchase_csv, export_purchase_xlsx
from src.utils.synonym_util import canonical, merge_synonyms


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.member_repo = MemberRepo(db)
        self.ingredient_repo = IngredientRepo(db)
        self.record_repo = RecipeRecordRepo(db)
        self.nutrition = NutritionService(db)

    def latest_record(self, family_id: int):
        """最新食谱生成记录（供导出采购清单重建）。"""
        return self.record_repo.latest(family_id)

    # ---------- 触发判断 ----------
    @staticmethod
    def should_trigger(main_dish_count: int, any_big_gap: bool) -> bool:
        return main_dish_count < 2 or any_big_gap

    def family_has_big_gap(self, family_id: int) -> bool:
        """遍历未删除成员：任一核心营养素缺口>30% 即 True。"""
        members = self.member_repo.list_active(family_id)
        if not members:
            return False
        for member in members:
            rni_map: dict[str, Decimal] = {}
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is not None:
                    rni_map[nut] = rni
            # 无反馈/无摄入时按 0 摄入计算缺口
            gaps = self.nutrition.member_gap(member, {nut: Decimal("0") for nut in rni_map})
            if any(g["status"] == "big_gap" for g in gaps):
                return True
        return False

    # ---------- 清单生成 ----------
    def build_purchase_list(
        self,
        family_id: int,
        result: RecipeGenerateResult,
        gap_detail: dict[int, list[dict]] | None = None,
    ) -> list[PurchaseItem]:
        """基于生成结果生成采购清单。

        简化一期实现：
        - 触发条件：主菜<2 或存在成员缺口>30%
        - 采购目标：按缺口营养素反推高含量食材（自建菜谱库二期完善），
          按 3 天需求量估算建议采购量。
        - 已录重量食材扣减家中存量，≤0 移除；无重量食材仅标记家中已有。
        """
        main_count = sum(1 for d in result.shared_dishes if d.is_main_dish)
        any_big = self.family_has_big_gap(family_id) or self._any_allocation_gap(result)
        if not self.should_trigger(main_count, any_big):
            return []

        # 收集家庭已有食材（按规范名归并）
        home_ingredients = self.ingredient_repo.list_valid(family_id)
        stock_by_name: dict[str, Decimal] = {}
        has_without_weight: set[str] = set()
        for ing in home_ingredients:
            key = canonical(ing.name)
            if ing.available_weight is None:
                has_without_weight.add(key)
            else:
                stock_by_name[key] = Decimal(str(ing.available_weight))

        # 缺口食材建议（一期：静态推荐食材映射，二期接自建菜谱库）
        suggest = self._suggest_foods_for_gap(family_id)

        items: list[PurchaseItem] = []
        for food, need_g in suggest.items():
            key = canonical(food)
            need = Decimal(str(need_g)) * PURCHASE_DAYS
            if key in stock_by_name:
                remain = need - stock_by_name[key]
                if remain <= 0:
                    continue  # 存量已满足，移除
                need = remain
                remark = ""
            elif key in has_without_weight:
                need = need  # 不扣减
                remark = REMARK_HAS_NO_WEIGHT
            else:
                remark = ""
            if need <= 0:
                continue
            priority = PURCHASE_P0
            items.append(
                PurchaseItem(
                    priority=priority,
                    food_name=canonical(food),
                    supplement_nutrient=[
                        NUTRIENT_LABEL_CN.get("protein", "蛋白质")
                    ],
                    suggest_amount_g=need,
                    remark=remark,
                )
            )

        return self._merge_and_sort(items)

    def _any_allocation_gap(self, result: RecipeGenerateResult) -> bool:
        """检查生成结果中是否有成员缺口>30%。"""
        for alloc in result.member_allocation:
            for gap in alloc.nutrition_gap:
                if float(gap.get("gap_ratio", 0) or 0) > 30:
                    return True
        return False

    def _suggest_foods_for_gap(self, family_id: int) -> dict[str, Decimal]:
        """按缺口营养素推荐高含量食材及每日建议量（克）。

        一期静态映射（二期由自建菜谱库/食谱库驱动）。
        """
        members = self.member_repo.list_active(family_id)
        need_foods: dict[str, Decimal] = {}
        mapping = {
            "protein": {"鸡胸肉": Decimal("50"), "鸡蛋": Decimal("30")},
            "calcium": {"牛奶": Decimal("200"), "豆腐": Decimal("50")},
            "iron": {"猪肝": Decimal("30"), "牛里脊": Decimal("40")},
            "zinc": {"生蚝": Decimal("40"), "瘦牛肉": Decimal("40")},
            "vitamin_a": {"胡萝卜": Decimal("60"), "菠菜": Decimal("60")},
            "vitamin_c": {"橙子": Decimal("80"), "青椒": Decimal("60")},
        }
        for member in members:
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is None:
                    continue
                # 无摄入按全缺口估算：推荐量按每人每日一份
                for food, amount in mapping.get(nut, {}).items():
                    need_foods[food] = need_foods.get(food, Decimal("0")) + amount
        return need_foods

    @staticmethod
    def _merge_and_sort(items: list[PurchaseItem]) -> list[PurchaseItem]:
        """同义词合并 + 优先级排序。"""
        merged: dict[str, dict] = {}
        for it in items:
            key = it.food_name
            if key in merged:
                old = merged[key]
                old["suggest_amount_g"] = Decimal(str(old["suggest_amount_g"])) + it.suggest_amount_g
                old["nutrients"] = sorted(set(old["nutrients"] + it.supplement_nutrient))
                old["remark"] = it.remark or old.get("remark", "")
            else:
                merged[key] = {
                    "priority": it.priority,
                    "food_name": key,
                    "nutrients": list(it.supplement_nutrient),
                    "suggest_amount_g": it.suggest_amount_g,
                    "remark": it.remark,
                }
        order = {PURCHASE_P0: 0, PURCHASE_P1: 1, PURCHASE_P2: 2}
        keys = sorted(merged, key=lambda k: (order.get(merged[k]["priority"], 9), k))
        return [
            PurchaseItem(
                priority=merged[k]["priority"],
                food_name=k,
                supplement_nutrient=merged[k]["nutrients"],
                suggest_amount_g=Decimal(str(merged[k]["suggest_amount_g"])),
                remark=merged[k]["remark"],
            )
            for k in keys
        ]

    # ---------- 导出 ----------
    def export_excel(self, items: list[PurchaseItem], fmt: str = "xlsx") -> str:
        rows = [
            {
                "priority": it.priority,
                "food_name": it.food_name,
                "supplement_nutrient": it.supplement_nutrient,
                "suggest_amount_g": float(it.suggest_amount_g),
                "remark": it.remark,
            }
            for it in items
        ]
        if fmt == "csv":
            return export_purchase_csv(rows)
        return export_purchase_xlsx(rows)

    def merge_display_count(self, names: list[str]) -> dict[str, int]:
        """同义词合并展示计数。"""
        return merge_synonyms(names)