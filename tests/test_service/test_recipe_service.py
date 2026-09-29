"""AI 食谱生成服务测试：Prompt 组装 / JSON 解析 / 结果规整 / 生成+落库 / 双模式。

双模式用例（对齐问题文档《期望 4 道只出 2 道》改造）：
- buy_supplement=False：仅使用家中现有食材，数量不足时如实返回 + tip 提示；
- buy_supplement=True：允许菜品使用家中没有的食材，缺料汇总为采购清单；
  数量不足如实返回，不补菜谱、不硬凑重复菜（宁缺毋滥）。
"""

from decimal import Decimal

import pytest

from app.modules.recipe.clients import MockLLMClient
from app.core.exceptions import LLMJsonParseError
from app.modules.recipe.models import RecipeGenerationRecord
from app.modules.family_member.schemas import MemberCreate
from app.modules.ingredient.schemas import IngredientConfirmIn, IngredientCreate
from app.modules.ingredient.service import IngredientService
from app.modules.recipe.schemas import (
    RecipeGenerateRequest,
    RecipeGenerateResult,
    SharedDish,
)
from app.modules.shopping_list.schemas import PurchaseItem
from app.modules.family_member.service import FamilyService
from app.modules.recipe.service import RecipeService


def _add_member(
    db,
    name: str = "小美",
    allergens: list[str] | None = None,
    dietary_restrictions: list[str] | None = None,
) -> int:
    svc = FamilyService(db)
    member = svc.create_member(
        MemberCreate(
            name=name,
            age=Decimal("30"),
            gender="female",
            diet_goal="normal",
            constitution=[],
            health_conditions=[],
            allergens=allergens or [],
            dietary_restrictions=dietary_restrictions or [],
        )
    )
    return member.id


def _add_ingredients(db, names: list[str]) -> None:
    """为家庭库存添加食材（可用重量选填，仅影响"家中已有"判定）。"""
    svc = IngredientService(db)
    svc.confirm_and_save(
        IngredientConfirmIn(
            family_id=1,
            items=[IngredientCreate(name=n) for n in names],
        )
    )


class TestParseLLMJson:
    def test_plain_json(self):
        text = '{"shared_dishes": [], "member_allocation": []}'
        data = RecipeService.parse_llm_json(text)
        assert data == {"shared_dishes": [], "member_allocation": []}

    def test_code_fence_json(self):
        text = '```json\n{"shared_dishes": [], "member_allocation": []}\n```'
        data = RecipeService.parse_llm_json(text)
        assert data["shared_dishes"] == []

    def test_broken_json_raises(self):
        with pytest.raises(LLMJsonParseError):
            RecipeService.parse_llm_json("这不是 JSON")

    def test_empty_raises(self):
        with pytest.raises(LLMJsonParseError):
            RecipeService.parse_llm_json("")


class TestNormalizeDishes:
    def test_skips_invalid_items(self):
        raw = [
            {"name": "番茄炒蛋", "category": "main", "is_main_dish": True},
            {"category": "main"},  # 无 name，跳过
            "not-a-dict",  # 非 dict，跳过
        ]
        dishes = RecipeService._normalize_dishes(raw)
        assert len(dishes) == 1
        assert dishes[0].name == "番茄炒蛋"
        assert dishes[0].is_main_dish is True


class TestBuildPrompt:
    def test_requires_member(self, db):
        from app.core.exceptions import BusinessException

        svc = RecipeService(db)
        with pytest.raises(BusinessException):
            svc.build_prompt(1, dish_count=4)

    def test_build_prompt_with_member(self, db):
        _add_member(db)
        svc = RecipeService(db)
        prompt, snapshot = svc.build_prompt(1, dish_count=4)
        assert "小美" in prompt
        assert snapshot["dish_count"] == 4
        assert len(snapshot["members"]) == 1


class TestGenerateAndPersist:
    def test_generate_with_mock(self, db):
        """仅库存模式：家中备齐 Mock 两道食材，Mock 返回 2 道，库内不足 4 道时如实返回 + tip 提示。"""
        member_id = _add_member(db)
        _add_ingredients(db, ["番茄", "鸡蛋", "油菜"])
        svc = RecipeService(db, llm_client=MockLLMClient())
        result = svc.generate(
            RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=False)
        )
        assert isinstance(result, RecipeGenerateResult)
        assert len(result.shared_dishes) == 2
        assert all(isinstance(d, SharedDish) for d in result.shared_dishes)
        assert result.member_allocation[0].dishes[0]["dish_name"] == "番茄炒蛋"
        # Mock 分配 member_id=1 应保留
        assert result.member_allocation[0].member_id == member_id
        # 数量不足提示（前端弹窗依据）
        assert result.tip

    def test_generate_supplement_mode_default(self, db):
        """推荐采购模式：不补菜谱凑数——模型出 2 道就 2 道，缺料进采购清单 + 诚实提示。"""
        member_id = _add_member(db)
        svc = RecipeService(db, llm_client=MockLLMClient())
        result = svc.generate(
            RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=True)
        )
        assert len(result.shared_dishes) == 2  # Mock 2 道，不再用菜谱库垫菜
        assert result.member_allocation[0].member_id == member_id
        # 库存为空 → 两道菜都缺料，采购清单只含家里没有的食材
        names = {p.food_name for p in result.purchase_list}
        assert names  # 缺料采购清单非空
        # 两轮生成后仍不足：提示如实说明（诚实提示不足，不硬凑）
        assert "少于期望的" in result.tip or "已按采购建议补齐" in result.tip

    def test_generate_home_only_returns_2_with_hint(self, db):
        """仅库存模式且库存备齐 Mock 两道：返回 Mock 的 2 道并给不足提示。"""
        _add_member(db)
        _add_ingredients(db, ["番茄", "鸡蛋", "油菜"])
        svc = RecipeService(db, llm_client=MockLLMClient())
        result = svc.generate(
            RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=False)
        )
        assert len(result.shared_dishes) == 2
        assert "库存食材" in result.tip

    def test_supplement_purchase_items_only_missing(self, db):
        """已有库存食材不进采购清单：食材全在家且模型两道菜无缺料 → 菜够就不推采购。"""
        _add_member(db)
        _add_ingredients(db, ["番茄", "鸡蛋", "油菜"])
        svc = RecipeService(db, llm_client=MockLLMClient())
        result = svc.generate(
            RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=True)
        )
        # Mock 两道菜食材全在家 → 不标需采购
        mock_dishes = [
            d for d in result.shared_dishes if d.name in ("番茄炒蛋", "清炒时蔬")
        ]
        assert mock_dishes and all(not d.needs_purchase for d in mock_dishes)
        # 无缺料 → 不推荐采购（菜够就不推）
        missing = {p.food_name for p in result.purchase_list}
        assert missing == set()  # 家里食材齐备，不需要采购

    def test_generate_and_persist_roundtrip(self, db):
        member_id = _add_member(db)
        _add_ingredients(db, ["番茄", "鸡蛋", "油菜"])
        svc = RecipeService(db, llm_client=MockLLMClient())
        result = svc.generate(
            RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=False)
        )
        assert result.member_allocation[0].member_id == member_id

        record: RecipeGenerationRecord = svc.persist(
            1,
            result,
            purchase_items=[
                PurchaseItem(food_name="鸡蛋", suggest_amount_g=Decimal("300"))
            ],
        )
        assert record.id > 0
        assert len(record.shared_dishes) == 2
        assert record.purchase_list[0]["food_name"] == "鸡蛋"

        latest = svc.list_records(1)
        assert len(latest) == 1
        assert latest[0].id == record.id
