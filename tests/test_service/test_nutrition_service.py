"""营养计算服务测试：gap_ratio / daily_rni / intake_from_amount / member_gap / 本地二次校验。"""
from decimal import Decimal

from app.core.constants import CORE_NUTRIENTS
from app.modules.family_member.models import Family
from app.modules.family_member.models import FamilyMember
from app.modules.family_member.schemas import MemberCreate
from app.modules.family_member.service import FamilyService
from app.modules.nutrition.service import NutritionService


def _make_member(db, *, gender="male", diet_goal="normal") -> FamilyMember:
    svc = FamilyService(db)
    return svc.create_member(
        MemberCreate(
            name="测试",
            age=Decimal("30"),
            gender=gender,
            diet_goal=diet_goal,
            constitution=[],
            health_conditions=[],
            allergens=[],
            dietary_restrictions=[],
        )
    )


class TestGapRatio:
    def test_gap_ratio_positive(self):
        svc = NutritionService.__new__(NutritionService)  # 不触库，静态逻辑
        svc.db = None
        assert svc.gap_ratio(Decimal("55"), Decimal("3.12")) == Decimal("94.33")

    def test_gap_ratio_zero_when_satisfied(self):
        svc = NutritionService.__new__(NutritionService)
        svc.db = None
        assert svc.gap_ratio(Decimal("55"), Decimal("60")) == Decimal("0")
        assert svc.gap_ratio(Decimal("55"), Decimal("55")) == Decimal("0")

    def test_gap_ratio_zero_rni(self):
        svc = NutritionService.__new__(NutritionService)
        svc.db = None
        assert svc.gap_ratio(Decimal("0"), Decimal("10")) == Decimal("0")


class TestDrisAndIntake:
    def test_daily_rni_by_target(self, db):
        svc = NutritionService(db)
        assert svc.daily_rni(_make_member(db), "protein") == Decimal("65")  # male -> adult_male
        assert svc.daily_rni(_make_member(db, gender="female"), "protein") == Decimal("55")

    def test_daily_rni_by_goal(self, db):
        svc = NutritionService(db)
        # 按年龄分档路由：婴幼儿（2 岁）走 baby 档；70 岁老人走 elderly 档
        baby = FamilyService(db).create_member(
            MemberCreate(
                name="宝宝", age=Decimal("2"), gender="female", diet_goal="baby",
                constitution=[], health_conditions=[], allergens=[], dietary_restrictions=[],
            )
        )
        assert svc.daily_rni(baby, "protein") == Decimal("20")
        elder = FamilyService(db).create_member(
            MemberCreate(
                name="爷爷", age=Decimal("70"), gender="male", diet_goal="elderly",
                constitution=[], health_conditions=[], allergens=[], dietary_restrictions=[],
            )
        )
        assert svc.daily_rni(elder, "protein") == Decimal("60")

    def test_food_nutrition_known(self, db):
        svc = NutritionService(db)
        nut = svc.food_nutrition("番茄")
        assert nut is not None
        assert nut["vitamin_c"] == Decimal("19.00")

    def test_food_nutrition_unknown(self, db):
        svc = NutritionService(db)
        assert svc.food_nutrition("不存在的食材") is None

    def test_intake_from_amount(self, db):
        svc = NutritionService(db)
        # 番茄 每100g 含蛋白质 0.9g，200g => 1.8g
        intake = svc.intake_from_amount("番茄", Decimal("200"))
        assert intake["protein"] == Decimal("1.80")


class TestMemberGap:
    def test_zero_intake_all_big_gap(self, db):
        svc = NutritionService(db)
        member = _make_member(db)
        gaps = svc.member_gap(member, {})
        assert len(gaps) == len(CORE_NUTRIENTS)
        assert all(g["status"] == "big_gap" for g in gaps)

    def test_full_intake_all_ok(self, db):
        svc = NutritionService(db)
        member = _make_member(db)
        # 假数据：全部营养满足 RNI（65 蛋白质 / 800 钙 / 12 铁 / 12.5 锌 / 0.8 VA / 100 VC）
        intake = {
            "protein": Decimal("65"),
            "calcium": Decimal("800"),
            "iron": Decimal("12"),
            "zinc": Decimal("12.5"),
            "vitamin_a": Decimal("0.8"),
            "vitamin_c": Decimal("100"),
        }
        gaps = svc.member_gap(member, intake)
        assert gaps
        assert all(g["status"] == "ok" for g in gaps)
        assert all(g["gap_ratio"] == Decimal("0") for g in gaps)

    def test_any_big_gap_flag(self, db):
        svc = NutritionService(db)
        member = _make_member(db)
        gaps = svc.member_gap(member, {"protein": Decimal("60")})
        assert svc.any_big_gap(gaps) is True  # 蛋白质 65->60 缺口小，但钙铁锌等全缺口


class TestLocalVerifyAllocation:
    def test_overrides_nutrition_gap_with_local_data(self, db):
        svc = NutritionService(db)
        member = _make_member(db)
        allocation = {
            "member_id": member.id,
            "member_name": "测试",
            "dishes": [{"dish_name": "番茄", "amount_g": 300}],
            "intake_advantage": [],
            "nutrition_gap": [],  # 模型未给缺口，本地应补算
        }
        result = svc.local_verify_allocation(member, allocation)
        assert len(result["nutrition_gap"]) == len(CORE_NUTRIENTS)
        # 300g 番茄蛋白质 2.7g < RNI 65，应存在大缺口
        protein_gap = next(g for g in result["nutrition_gap"] if g["nutrient"] == "protein")
        assert protein_gap["actual"] == 2.7
        assert protein_gap["status"] == "big_gap"


class TestDecompose:
    def test_decompose_single_food(self, db):
        svc = NutritionService(db)
        # 无 record：按单食材分解，200g 番茄蛋白 1.8g
        total = svc.decompose_dish("番茄", Decimal("200"))
        assert total["protein"] == Decimal("1.80")

    def test_summarize_nutrients(self, db):
        svc = NutritionService(db)
        total = svc.summarize_nutrients(
            [{"protein": Decimal("1.8")}, {"protein": Decimal("1.2")}]
        )
        assert total["protein"] == Decimal("3.00")