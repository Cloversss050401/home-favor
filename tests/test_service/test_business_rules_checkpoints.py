"""硬性业务规则检查点验证测试（CHK-01 ~ CHK-08）。

每个测试对应一项缺陷报告检查点，验证代码已正确落地对应业务规则。
验收方式：8 项全部通过后标记「已核查」。
"""
from datetime import date
from decimal import Decimal

import pytest

from src.config.constants import (
    EXCEED_RATIO,
    MEMBER_FAMILY_LIMIT,
    PURCHASE_DAYS,
    REMARK_HAS_NO_WEIGHT,
)
from src.exceptions.business_exception import MemberLimitExceeded
from src.schemas.feedback_schema import FeedbackCreate, FeedbackItem
from src.schemas.ingredient_schema import IngredientConfirmIn, IngredientCreate
from src.schemas.member_schema import MemberCreate
from src.schemas.recipe_schema import (
    RecipeGenerateResult,
    SharedDish,
)
from src.services.family_service import FamilyService
from src.services.feedback_service import FeedbackService
from src.services.ingredient_service import IngredientService
from src.services.nutrition_service import NutritionService
from src.services.purchase_service import PurchaseService
from src.services.report_service import ReportService
from src.utils.synonym_util import SYNONYM_FILE, canonical


# ---------- 辅助函数 ----------
def _member_payload(name: str = "测试", **overrides) -> MemberCreate:
    data = {
        "name": name,
        "age": Decimal("30"),
        "gender": "female",
        "diet_goal": "normal",
        "constitution": [],
        "health_conditions": [],
        "allergens": [],
        "dietary_restrictions": [],
    }
    data.update(overrides)
    return MemberCreate(**data)


def _add_member(db, **overrides):
    return FamilyService(db).create_member(_member_payload(**overrides))


def _two_main_dishes_result() -> RecipeGenerateResult:
    return RecipeGenerateResult(
        shared_dishes=[
            SharedDish(name="番茄炒蛋", category="main", is_main_dish=True),
            SharedDish(name="清炒时蔬", category="main", is_main_dish=True),
        ],
        member_allocation=[],
        purchase_list=[],
    )


# ==================== CHK-01 ====================
class TestCHK01NutrientGapTrigger:
    """核心营养素缺口触发采购：缺口>30% 或 主菜<2 触发采购。"""

    def test_gap_ratio_boundary_29_not_big_gap(self):
        """缺口 29% 不视为大缺口（不触发采购）。"""
        svc = NutritionService.__new__(NutritionService)
        svc.db = None
        # rni=100, actual=71 => gap=(100-71)/100*100=29%
        ratio = svc.gap_ratio(Decimal("100"), Decimal("71"))
        assert ratio == Decimal("29.00")
        assert not (ratio > 30)  # 29% 不触发

    def test_gap_ratio_boundary_30_not_big_gap(self):
        """缺口恰好 30% 不触发（规则为 >30%）。"""
        svc = NutritionService.__new__(NutritionService)
        svc.db = None
        ratio = svc.gap_ratio(Decimal("100"), Decimal("70"))
        assert ratio == Decimal("30.00")
        assert not (ratio > 30)  # 30% 不触发（>30% 才触发）

    def test_gap_ratio_boundary_31_is_big_gap(self):
        """缺口 31% 触发大缺口（>30%）。"""
        svc = NutritionService.__new__(NutritionService)
        svc.db = None
        ratio = svc.gap_ratio(Decimal("100"), Decimal("69"))
        assert ratio == Decimal("31.00")
        assert ratio > 30  # 31% 触发

    def test_should_trigger_main_dish_boundary(self):
        """主菜 1 道触发，主菜 2 道且无缺口不触发。"""
        assert PurchaseService.should_trigger(1, False) is True   # 主菜<2
        assert PurchaseService.should_trigger(2, False) is False  # 主菜>=2 且无大缺口
        assert PurchaseService.should_trigger(2, True) is True    # 主菜>=2 但有大缺口

    def test_member_gap_status_matches_threshold(self, db):
        """member_gap 中 status 在 30% 边界正确区分 gap / big_gap。"""
        svc = NutritionService(db)
        member = _add_member(db)  # female: protein RNI=55
        # 蛋白质摄入=38.5 => 缺口=30%，应为 gap 而非 big_gap
        # 其余营养全部满足，避免干扰 any_big_gap 判断
        intake = {
            "protein": Decimal("38.5"),      # gap=30%
            "calcium": Decimal("800"),       # ok
            "iron": Decimal("20"),           # ok
            "zinc": Decimal("7.5"),          # ok
            "vitamin_a": Decimal("0.7"),     # ok
            "vitamin_c": Decimal("100"),     # ok
        }
        gaps = svc.member_gap(member, intake)
        protein = next(g for g in gaps if g["nutrient"] == "protein")
        assert protein["gap_ratio"] == Decimal("30.00")
        assert protein["status"] == "gap"
        assert svc.any_big_gap(gaps) is False


# ==================== CHK-02 ====================
class TestCHK02PurchaseThreeDays:
    """采购清单满足全家 3 天需求：天数乘数硬编码为 3。"""

    def test_purchase_days_constant_is_3(self):
        """常量 PURCHASE_DAYS 必须为 3。"""
        assert PURCHASE_DAYS == 3

    def test_suggest_amount_multiplied_by_3_days(self, db):
        """建议采购量 = 每日推荐量 × 3 天。"""
        _add_member(db)
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        # 鸡胸肉每日 50g × 3 天 = 150g
        chicken = next((i for i in items if i.food_name == "鸡胸肉"), None)
        assert chicken is not None
        assert chicken.suggest_amount_g == Decimal("50") * PURCHASE_DAYS


# ==================== CHK-03 ====================
class TestCHK03OnlyWeightDeductsStock:
    """仅录入重量时才扣减库存；无重量仅标记家中已有。"""

    def test_no_weight_ingredient_not_deducted(self, db):
        """家中已有但无重量的食材：不扣减，标记 REMARK_HAS_NO_WEIGHT。"""
        _add_member(db)
        IngredientService(db).confirm_and_save(
            IngredientConfirmIn(
                family_id=1,
                items=[IngredientCreate(name="鸡蛋")],  # 无重量
            )
        )
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        egg = next((i for i in items if i.food_name == "鸡蛋"), None)
        assert egg is not None
        assert egg.remark == REMARK_HAS_NO_WEIGHT

    def test_weight_ingredient_deducted(self, db):
        """有重量的食材：扣减存量，扣减后不足部分才出现在清单。"""
        _add_member(db)
        IngredientService(db).confirm_and_save(
            IngredientConfirmIn(
                family_id=1,
                items=[IngredientCreate(name="鸡蛋", available_weight=Decimal("5000"))],
            )
        )
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        names = {i.food_name for i in items}
        # 鸡蛋每日 30g × 3 天 = 90g，存量 5000g 远超需求，应被移除
        assert "鸡蛋" not in names


# ==================== CHK-04 ====================
class TestCHK04SynonymDictionaryMerge:
    """食材同义词字典合并：synonyms.json 存在且被采购服务加载使用。"""

    def test_synonyms_file_exists(self):
        """同义词字典文件必须存在。"""
        assert SYNONYM_FILE.exists(), "resources/dict/synonyms.json 不存在"

    def test_canonical_maps_alias(self):
        """别名应映射到规范名。"""
        assert canonical("西红柿") == "番茄"
        assert canonical("洋鸡蛋") == "鸡蛋"

    def test_purchase_list_uses_canonical_names(self, db):
        """采购清单合并时使用规范名（同义词归并）。"""
        _add_member(db)
        # 家中存量用别名录入，采购建议用规范名，两者应正确匹配扣减
        IngredientService(db).confirm_and_save(
            IngredientConfirmIn(
                family_id=1,
                items=[IngredientCreate(name="西红柿", available_weight=Decimal("5000"))],
            )
        )
        svc = PurchaseService(db)
        items = svc.build_purchase_list(1, _two_main_dishes_result())
        names = {i.food_name for i in items}
        # 番茄（规范名）存量已满足，不应出现在采购清单
        assert "番茄" not in names
        assert "西红柿" not in names


# ==================== CHK-05 ====================
class TestCHK05MemberLimitEight:
    """成员最多 8 人（含逻辑删除过滤）；超限返回 400。"""

    def test_ninth_member_raises_400(self, db):
        """第 9 人创建失败，异常状态码为 400。"""
        svc = FamilyService(db)
        for i in range(MEMBER_FAMILY_LIMIT):
            svc.create_member(_member_payload(name=f"成员{i}"))
        with pytest.raises(MemberLimitExceeded) as exc:
            svc.create_member(_member_payload(name="第九人"))
        assert exc.value.status_code == 400

    def test_soft_deleted_member_frees_slot(self, db):
        """逻辑删除的成员不计入活跃数，删除后可再创建第 9 人。"""
        svc = FamilyService(db)
        members = [svc.create_member(_member_payload(name=f"成员{i}")) for i in range(MEMBER_FAMILY_LIMIT)]
        # 已满 8 人，第 9 人失败
        with pytest.raises(MemberLimitExceeded):
            svc.create_member(_member_payload(name="第九人"))
        # 逻辑删除 1 人后释放名额
        svc.delete_member(members[0].id)
        # 现在可以再创建
        new_member = svc.create_member(_member_payload(name="新成员"))
        assert new_member.id > 0

    def test_controller_returns_400_on_limit(self, client):
        """通过 API 创建第 9 人应返回 400 状态码。"""
        for i in range(MEMBER_FAMILY_LIMIT):
            r = client.post(
                "/api/members",
                json=_member_payload(name=f"成员{i}").model_dump(mode="json"),
            )
            assert r.status_code == 201
        r = client.post(
            "/api/members",
            json=_member_payload(name="第九人").model_dump(mode="json"),
        )
        assert r.status_code == 400


# ==================== CHK-06 ====================
class TestCHK06LogicalDeleteOnly:
    """所有删除接口均为逻辑删除，禁止物理删除。"""

    def test_member_soft_delete_preserves_record(self, db):
        """成员删除：is_deleted=1，记录仍在数据库中。"""
        from src.models.member_model import FamilyMember

        svc = FamilyService(db)
        member = svc.create_member(_member_payload())
        svc.delete_member(member.id)
        # 直接查库验证记录仍存在（仅 is_deleted=1）
        row = db.get(FamilyMember, member.id)
        assert row is not None
        assert row.is_deleted == 1

    def test_ingredient_soft_delete_preserves_record(self, db):
        """食材删除：is_valid=0，记录仍在数据库中。"""
        from src.models.ingredient_model import HouseholdIngredient

        svc = IngredientService(db)
        svc.confirm_and_save(
            IngredientConfirmIn(
                family_id=1,
                items=[IngredientCreate(name="番茄", available_weight=Decimal("500"))],
            )
        )
        item = svc.list_ingredients()[0]
        svc.delete_ingredient(item.id)
        row = db.get(HouseholdIngredient, item.id)
        assert row is not None
        assert row.is_valid == 0

    def test_no_physical_delete_in_source(self):
        """源代码中不存在 db.delete / session.delete 物理删除调用。"""
        import subprocess
        import sys
        from pathlib import Path

        src = Path(__file__).resolve().parents[2] / "src"
        result = subprocess.run(
            [sys.executable, "-c",
             f"import pathlib; p=pathlib.Path(r'{src}'); "
             "files=list(p.rglob('*.py')); "
             "hits=[str(f) for f in files if 'db.delete' in f.read_text(encoding='utf-8') or 'session.delete' in f.read_text(encoding='utf-8')]; "
             "print('\\n'.join(hits))"],
            capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", f"发现物理删除调用: {result.stdout.strip()}"


# ==================== CHK-07 ====================
class TestCHK07ReportOnlyFeedbackDays:
    """周营养报告仅统计有反馈记录的日期。"""

    def test_effective_days_equals_feedback_days(self, db):
        """一周 7 天仅 1 天有反馈，effective_days 应为 1。"""
        member_id = _add_member(db).id
        FeedbackService(db).create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),  # 仅周五有反馈
                items=[
                    FeedbackItem(member_id=member_id, dish_name="番茄", amount_g=Decimal("200")),
                ],
            )
        )
        svc = ReportService(db)
        report = svc.build_report(1, date(2026, 9, 21), date(2026, 9, 27))
        assert report["effective_days"] == 1
        nutrients = report["members"][0]["nutrients"]
        protein = next(n for n in nutrients if n["nutrient_code"] == "protein")
        # 仅 1 天有效，摄入 = 200g 番茄蛋白 1.8g
        assert protein["effective_days"] == 1
        assert protein["total_intake"] == 1.8


# ==================== CHK-08 ====================
class TestCHK08ExceedThreshold1_2RNI:
    """超标阈值为 1.2 × RNI：实际摄入 > 1.2×RNI 才标记超标。"""

    def test_exceed_ratio_constant(self):
        """超标阈值常量必须为 1.2。"""
        assert EXCEED_RATIO == 1.2

    def test_intake_below_threshold_not_exceeded(self, db):
        """实际摄入 ≤ 1.2×RNI 不超标。"""
        member_id = _add_member(db).id  # female, protein RNI=55, 阈值=66
        # 400g 鸡蛋蛋白 = 13.3*4 = 53.2g < 66，不超标
        FeedbackService(db).create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),
                items=[
                    FeedbackItem(member_id=member_id, dish_name="鸡蛋", amount_g=Decimal("400")),
                ],
            )
        )
        report = ReportService(db).build_report(1, date(2026, 9, 21), date(2026, 9, 27))
        protein = next(
            n for n in report["members"][0]["nutrients"]
            if n["nutrient_code"] == "protein"
        )
        assert protein["exceeded"] is False

    def test_intake_above_threshold_exceeded(self, db):
        """实际摄入 > 1.2×RNI 标记超标。"""
        member_id = _add_member(db).id  # female, protein RNI=55, 阈值=66
        # 600g 鸡蛋蛋白 = 13.3*6 = 79.8g > 66，超标
        FeedbackService(db).create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),
                items=[
                    FeedbackItem(member_id=member_id, dish_name="鸡蛋", amount_g=Decimal("600")),
                ],
            )
        )
        report = ReportService(db).build_report(1, date(2026, 9, 21), date(2026, 9, 27))
        protein = next(
            n for n in report["members"][0]["nutrients"]
            if n["nutrient_code"] == "protein"
        )
        assert protein["exceeded"] is True
