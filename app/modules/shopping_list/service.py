"""智能采购清单业务。

对齐硬性业务规则第 2 条：
- 触发条件：任意成员核心营养素缺口>30% 或 主菜<2 道
- 计算口径：满足全家 3 天需求；仅已录重量才扣减存量；扣减后≤0 移除
- 无重量食材：标记“家中已有”，不扣减
- 同义词合并同类食材；P0/P1/P2 排序；导出 Excel 字段固定
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import (
    GAP_ADVICE_CN,
    is_seasoning,
    GAP_CONSECUTIVE_DAYS,
    HISTORY_WINDOW_DAYS,
    NUTRIENT_LABEL_CN,
    PURCHASE_DAYS,
    PURCHASE_P0,
    PURCHASE_P1,
    PURCHASE_P2,
    REMARK_ALREADY_ENOUGH,
    REMARK_HAS_NO_WEIGHT,
)
from app.modules.ingredient.repository import IngredientRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.recipe.repository import RecipeRecordRepo
from app.modules.recipe.schemas import RecipeGenerateResult
from app.modules.shopping_list.schemas import PurchaseItem
from app.modules.nutrition.service import NutritionService, gap_foods_for
from app.common.utils import export_purchase_csv, export_purchase_xlsx
from app.common.utils import canonical, merge_synonyms


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
            gaps = self.nutrition.member_gap(
                member, {nut: Decimal("0") for nut in rni_map}
            )
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
        # 食物 -> 对应缺口营养素中文名（采购"为什么买"用途，不标个人）
        gap_nutrients: dict[str, list[str]] = self._gap_food_nutrients(
            family_id
        )

        items: list[PurchaseItem] = []
        for food, need_g in suggest.items():
            if is_seasoning(food):
                continue
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
            nut_names = gap_nutrients.get(canonical(food), [])
            remark = remark or ("补" + "、".join(nut_names) if nut_names else "")
            items.append(
                PurchaseItem(
                    priority=priority,
                    food_name=canonical(food),
                    supplement_nutrient=nut_names or [],
                    suggest_amount_g=need,
                    remark=remark,
                    target_member="",
                    gap_ratio=0.0,
                )
            )

        # 历史联动：最近窗口内同成员同营养素缺口>30% 累计满 3 天 → 必买项（★）
        items = self._merge_and_sort(items)
        items = self._merge_must_buy(items, family_id)
        return items

    def _any_allocation_gap(self, result: RecipeGenerateResult) -> bool:
        """检查生成结果中是否有成员缺口>30%。"""
        for alloc in result.member_allocation:
            for gap in alloc.nutrition_gap:
                if float(gap.get("gap_ratio", 0) or 0) > 30:
                    return True
        return False

    # ---------- 历史联动（基础版）----------
    def _history_consecutive_gaps(
        self, family_id: int, today
    ) -> dict[tuple[int, str], dict]:
        """统计最近 HISTORY_WINDOW_DAYS 天内：成员×营养素 缺口>30% 的天数。

        口径与周报一致：实际反馈优先、AI 预填/最后食谱估算兜底（每日混合）。
        返回 {(member_id, nutrient): {member_name, nutrient, gap_days, rni}}
        """
        from datetime import timedelta

        from app.modules.nutrition.service import ReportService

        start = today - timedelta(days=HISTORY_WINDOW_DAYS)
        end = today
        report_svc = ReportService(self.db)
        members = self.member_repo.list_active(family_id)
        feedback_rows = report_svc.feedback_repo.list_by_range(family_id, start, end)
        if not feedback_rows:
            return {}
        from app.common.utils import date_list

        days = [d for d in date_list(start, end)]
        result: dict[tuple[int, str], dict] = {}
        for member in members:
            daily_full, _src = report_svc._member_daily_breakdown(
                family_id, member, feedback_rows, days
            )
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is None:
                    continue
                count = report_svc._consecutive_gaps(member, daily_full, days, nut, rni)
                if count >= GAP_CONSECUTIVE_DAYS:
                    result[(member.id, nut)] = {
                        "member_id": member.id,
                        "member_name": member.name,
                        "nutrient": nut,
                        "nutrient_name": NUTRIENT_LABEL_CN.get(nut, nut),
                        "gap_days": count,
                        "rni": float(rni),
                    }
        return result

    def _merge_must_buy(
        self, items: list[PurchaseItem], family_id: int
    ) -> list[PurchaseItem]:
        """把历史连续缺口升级的必买食材合并进采购清单（★ + 推荐克数）。"""
        from datetime import date as _date

        gaps = self._history_consecutive_gaps(family_id, _date.today())
        if not gaps:
            return items
        must_by_food: dict[str, dict] = {}
        for (mid, nut), info in gaps.items():
            member = self.member_repo.get(mid)
            foods = gap_foods_for(member, nut)[:2] if member else []
            for food in foods:
                key = canonical(food)
                if key not in must_by_food:
                    must_by_food[key] = {
                        "food": food,
                        "member_name": info["member_name"],
                        "nutrient": nut,
                        "nutrient_name": info["nutrient_name"],
                        "gap_days": info["gap_days"],
                        "amount_g": Decimal("100"),
                    }
                else:
                    cur = must_by_food[key]
                    if info["gap_days"] > cur["gap_days"]:
                        cur["member_name"] = info["member_name"]
                        cur["nutrient"] = nut
                        cur["nutrient_name"] = info["nutrient_name"]
                        cur["gap_days"] = info["gap_days"]
        merged = {it.food_name: it for it in items}
        for key, info in must_by_food.items():
            if key in merged:
                old_it = merged[key]
                merged[key] = PurchaseItem(
                    priority=old_it.priority,
                    food_name=key,
                    supplement_nutrient=old_it.supplement_nutrient,
                    suggest_amount_g=old_it.suggest_amount_g + info["amount_g"],
                    remark=old_it.remark,
                    target_member="",
                    gap_ratio=float(info["gap_days"] * 30),
                    is_must_buy=True,
                )
            else:
                merged[key] = PurchaseItem(
                    priority=PURCHASE_P0,
                    food_name=key,
                    supplement_nutrient=[info["nutrient_name"]],
                    suggest_amount_g=info["amount_g"] * PURCHASE_DAYS,
                    remark=f"连续{info['gap_days']}天缺{info['nutrient_name']}，必买补货",
                    target_member="",
                    gap_ratio=float(info["gap_days"] * 30),
                    is_must_buy=True,
                )
        order = {PURCHASE_P0: 0, PURCHASE_P1: 1, PURCHASE_P2: 2}
        return sorted(
            merged.values(),
            key=lambda it: (0 if it.is_must_buy else 1, order.get(it.priority, 9), it.food_name),
        )

    def _gap_food_nutrients(self, family_id: int) -> dict[str, list[str]]:
        """食材 -> 对应缺口营养素中文名（采购清单"为什么买"用途）。"""
        members = self.member_repo.list_active(family_id)
        out: dict[str, list[str]] = {}
        for member in members:
            gaps = self.nutrition.member_gap(
                member,
                {
                    nut: Decimal("0")
                    for nut in [
                        "protein",
                        "calcium",
                        "iron",
                        "zinc",
                        "vitamin_a",
                        "vitamin_c",
                    ]
                },
            )
            name_by_nut = {g["nutrient"]: g["nutrient_name"] for g in gaps}
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                label = name_by_nut.get(nut)
                if not label:
                    continue
                for food in gap_foods_for(member, nut)[:2]:
                    key = canonical(food)
                    lst = out.setdefault(key, [])
                    if label not in lst:
                        lst.append(label)
        return out

    def _suggest_foods_for_gap(self, family_id: int) -> dict[str, Decimal]:
        """按缺口营养素推荐高含量食材及每日建议量（克）。

        按成员类型分套（宝宝→软烂安全、素食→植物源+蛋奶、通用），
        避免给素食者/婴幼儿推荐猪肝、牛肉等。
        """
        members = self.member_repo.list_active(family_id)
        need_foods: dict[str, Decimal] = {}
        default_amount = {
            "protein": Decimal("50"),
            "calcium": Decimal("100"),
            "iron": Decimal("40"),
            "zinc": Decimal("40"),
            "vitamin_a": Decimal("60"),
            "vitamin_c": Decimal("80"),
        }
        for member in members:
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is None:
                    continue
                # 无摄入按全缺口估算：推荐量按每人每日一份
                for food in gap_foods_for(member, nut)[:2]:
                    need_foods[food] = need_foods.get(food, Decimal("0")) + default_amount.get(
                        nut, Decimal("50")
                    )
        return need_foods

    def _target_member_by_food(self, family_id: int) -> dict[str, tuple[str, float]]:
        """食材 -> (优先补齐成员姓名, 缺口比例%)。

        对每种缺口推荐食材，找到缺口比例最大的成员（前端契约"优先补齐成员/缺口比例"）。
        """
        members = self.member_repo.list_active(family_id)
        # 按成员类型分套的食材集合（与 _suggest_foods_for_gap 一致）；
        # 每个食材收集所有缺口>0 的成员，取缺口最大的前 2 人标注（不显得只给一人买菜）
        per_food: dict[str, list[tuple[str, float]]] = {}
        for member in members:
            gaps = self.nutrition.member_gap(
                member,
                {
                    nut: Decimal("0")
                    for nut in [
                        "protein",
                        "calcium",
                        "iron",
                        "zinc",
                        "vitamin_a",
                        "vitamin_c",
                    ]
                },
            )
            gap_by_nut = {g["nutrient"]: float(g["gap_ratio"]) for g in gaps}
            for nut in ["protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"]:
                ratio = gap_by_nut.get(nut, 0.0)
                for food in gap_foods_for(member, nut)[:2]:
                    per_food.setdefault(canonical(food), []).append((member.name, ratio))
        result: dict[str, tuple[str, float]] = {}
        for key, lst in per_food.items():
            # 同一成员因多个营养素命中同一食材会重复，先去重再取前 2 人
            uniq: list[tuple[str, float]] = []
            seen: set[str] = set()
            for name, r in sorted(lst, key=lambda x: x[1], reverse=True):
                if name not in seen:
                    seen.add(name)
                    uniq.append((name, r))
            top = [name for name, _r in uniq[:2] if _r > 0]
            result[key] = ("、".join(top) if top else uniq[0][0], uniq[0][1])
        return result

    @staticmethod
    def _merge_and_sort(items: list[PurchaseItem]) -> list[PurchaseItem]:
        """同义词合并 + 优先级排序。"""
        merged: dict[str, dict] = {}
        for it in items:
            key = it.food_name
            if key in merged:
                old = merged[key]
                old["suggest_amount_g"] = (
                    Decimal(str(old["suggest_amount_g"])) + it.suggest_amount_g
                )
                old["nutrients"] = sorted(
                    set(old["nutrients"] + it.supplement_nutrient)
                )
                old["remark"] = it.remark or old.get("remark", "")
                old["is_must_buy"] = old.get("is_must_buy") or it.is_must_buy
                # 取缺口比例更大的成员作为"优先补齐成员"
                if it.gap_ratio > float(old.get("gap_ratio", 0)):
                    old["target_member"] = it.target_member
                    old["gap_ratio"] = it.gap_ratio
            else:
                merged[key] = {
                    "priority": it.priority,
                    "food_name": key,
                    "nutrients": list(it.supplement_nutrient),
                    "suggest_amount_g": it.suggest_amount_g,
                    "remark": it.remark,
                    "target_member": it.target_member,
                    "gap_ratio": it.gap_ratio,
                    "is_must_buy": it.is_must_buy,
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
                target_member=merged[k]["target_member"],
                gap_ratio=float(merged[k]["gap_ratio"]),
                is_must_buy=bool(merged[k].get("is_must_buy", False)),
            )
            for k in keys
        ]

    @staticmethod
    def merge_items(items: list[PurchaseItem]) -> list[PurchaseItem]:
        """公共入口：同义词合并 + 优先级排序（供生成链路合并补菜缺料与缺口触发清单）。"""
        return PurchaseService._merge_and_sort(items)

    # ---------- 导出 ----------
    def export_excel(self, items: list[PurchaseItem], fmt: str = "xlsx") -> str:
        rows = [
            {
                "priority": it.priority,
                "food_name": it.food_name,
                "supplement_nutrient": it.supplement_nutrient,
                "suggest_amount_g": float(it.suggest_amount_g),
                "remark": it.remark,
                "target_member": it.target_member,
                "gap_ratio": float(it.gap_ratio),
            }
            for it in items
        ]
        if fmt == "csv":
            return export_purchase_csv(rows)
        return export_purchase_xlsx(rows)

    def merge_display_count(self, names: list[str]) -> dict[str, int]:
        """同义词合并展示计数。"""
        return merge_synonyms(names)
