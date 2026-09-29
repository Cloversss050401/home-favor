"""智能采购服务测试：触发判断 / family_has_big_gap / build_purchase_list / 导出。"""
from decimal import Decimal

from app.modules.family_member.schemas import MemberCreate
from app.modules.recipe.schemas import RecipeGenerateResult, SharedDish
from app.modules.shopping_list.schemas import PurchaseItem
from app.modules.family_member.service import FamilyService
from app.modules.ingredient.service import IngredientService
from app.modules.shopping_list.service import PurchaseService
from app.modules.ingredient.schemas import IngredientConfirmIn, IngredientCreate


def _add_member(db, name="小美"):
    svc = FamilyService(db)
    return svc.create_member(
        MemberCreate(
            name=name,
            age=Decimal("30"),
            gender="female",
            diet_goal="normal",
            constitution=[],
            health_conditions=[],
            allergens=[],
            dietary_restrictions=[],
        )
    )


def _two_main_dishes_result() -> RecipeGenerateResult:
    return RecipeGenerateResult(
        shared_dishes=[
            SharedDish(name="番茄炒蛋", category="main", is_main_dish=True),
            SharedDish(name="清炒时蔬", category="main", is_main_dish=True),
        ],
        member_allocation=[
            {
                "member_id": 1,
                "member_name": "小美",
                "dishes": [],
                "intake_advantage": [],
                "nutrition_gap": [],
            }
        ],
        purchase_list=[],
    )


class TestShouldTrigger:
    def test_too_few_main_dishes_triggers(self):
        assert PurchaseService.should_trigger(1, False) is True

    def test_big_gap_triggers(self):
        assert PurchaseService.should_trigger(2, True) is True

    def test_no_trigger(self):
        assert PurchaseService.should_trigger(2, False) is False


class TestFamilyHasBigGap:
    def test_no_members_false(self, db):
        assert PurchaseService(db).family_has_big_gap(1) is False

    def test_member_zero_intake_true(self, db):
        _add_member(db)
        # 无反馈时按 0 摄入计算缺口 -> big_gap
        assert PurchaseService(db).family_has_big_gap(1) is True


class TestBuildPurchaseList:
    def test_not_triggered_returns_empty(self, db):
        svc = PurchaseService(db)
        # 无成员 + 主菜=2 -> 不触发
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        assert items == []

    def test_triggered_generates_items(self, db):
        _add_member(db)
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        assert len(items) > 0
        # 字段完备
        first: PurchaseItem = items[0]
        assert first.food_name
        assert first.priority == "P0"
        assert first.suggest_amount_g > 0
        assert first.supplement_nutrient

    def test_stock_deduction_removes_satisfied(self, db):
        _add_member(db)
        # 家里已有 5000g 鸡胸肉：3 天需求应被扣减 / 若需求小于存量则该食材不出现
        IngredientService(db).confirm_and_save(
            IngredientConfirmIn(
                family_id=1,
                items=[IngredientCreate(name="鸡胸肉", available_weight=Decimal("5000"))],
            )
        )
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        stock_names = {i.food_name for i in items}
        assert "鸡胸肉" not in stock_names  # 存量已满足需求被移除

    def test_merge_synonyms(self, db):
        names = ["西红柿", "番茄"]
        merged = PurchaseService(db).merge_display_count(names)
        assert merged == {"番茄": 2}

    def test_merge_items_combines_amounts(self, db):
        """公共 merge_items：同名项合并克数、营养标签去重、按优先级排序（同上一次合并逻辑）。"""
        items = [
            PurchaseItem(
                food_name="番茄",
                suggest_amount_g=Decimal("200"),
                priority="P0",
                supplement_nutrient=["维生素C"],
                gap_ratio=0.35,
                target_member="小美",
            ),
            PurchaseItem(
                food_name="番茄",
                suggest_amount_g=Decimal("300"),
                priority="P0",
                supplement_nutrient=["维生素C"],
                gap_ratio=0.50,
                target_member="小明",
            ),
            PurchaseItem(food_name="鸡蛋", suggest_amount_g=Decimal("120"), priority="P1"),
        ]
        merged = PurchaseService.merge_items(items)
        assert len(merged) == 2
        by_name = {i.food_name: i for i in merged}
        assert by_name["番茄"].suggest_amount_g == Decimal("500")
        assert by_name["番茄"].gap_ratio == 0.50  # 缺口更大的成员胜出
        assert by_name["番茄"].target_member == "小明"
        assert by_name["番茄"].supplement_nutrient
        # P0 组优先于 P1
        names = [i.food_name for i in merged]
        assert names.index("番茄") < names.index("鸡蛋")


class TestExportExcel:
    def test_export_csv(self, db):
        svc = PurchaseService(db)
        items = [PurchaseItem(food_name="鸡蛋", suggest_amount_g=Decimal("300"))]
        path = svc.export_excel(items, fmt="csv")
        assert path.endswith(".csv")
        import os

        assert os.path.exists(path)
        os.remove(path)

    def test_export_xlsx(self, db):
        svc = PurchaseService(db)
        items = [PurchaseItem(food_name="鸡蛋", suggest_amount_g=Decimal("300"))]
        path = svc.export_excel(items, fmt="xlsx")
        assert path.endswith(".xlsx")
        import os

        assert os.path.exists(path)
        os.remove(path)