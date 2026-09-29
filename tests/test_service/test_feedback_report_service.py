"""反馈 + 周报服务测试：手动反馈 / 一键全选 / 周报聚合。"""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.recipe.clients import MockLLMClient
from app.core.exceptions import ReportNotReady
from app.modules.nutrition.schemas import FeedbackCreate, FeedbackItem
from app.modules.family_member.schemas import MemberCreate
from app.modules.recipe.schemas import RecipeGenerateRequest
from app.modules.family_member.service import FamilyService
from app.modules.nutrition.service import FeedbackService
from app.modules.recipe.service import RecipeService
from app.modules.nutrition.service import ReportService


def _add_member(db, name="小美") -> int:
    svc = FamilyService(db)
    member = svc.create_member(
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
    return member.id


def _generate_record(db):
    """生成一条食谱落库记录（库存备齐 Mock 两道食材，严格模式下仍能出菜）。"""
    from app.modules.ingredient.schemas import IngredientConfirmIn, IngredientCreate
    from app.modules.ingredient.service import IngredientService

    IngredientService(db).confirm_and_save(
        IngredientConfirmIn(
            family_id=1,
            items=[IngredientCreate(name=n) for n in ("番茄", "鸡蛋", "油菜")],
        )
    )
    svc = RecipeService(db, llm_client=MockLLMClient())
    result = svc.generate(
        RecipeGenerateRequest(family_id=1, dish_count=4, buy_supplement=False)
    )
    return svc.persist(1, result)


class TestCreateFeedback:
    def test_manual_feedback(self, db):
        member_id = _add_member(db)
        svc = FeedbackService(db)
        count = svc.create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),
                use_ai_amount=False,
                items=[
                    FeedbackItem(member_id=member_id, dish_name="番茄炒蛋", amount_g=Decimal("150")),
                ],
            )
        )
        assert count == 1
        rows = svc.list_feedback(1, date(2026, 9, 21), date(2026, 9, 27))
        assert len(rows) == 1
        assert rows[0].is_ai_recommended == 0

    def test_feedback_ai_amount(self, db):
        member_id = _add_member(db)
        record = _generate_record(db)
        svc = FeedbackService(db)
        count = svc.create_feedback(
            FeedbackCreate(
                family_id=1,
                recipe_record_id=record.id,
                eaten_date=date(2026, 9, 25),
                use_ai_amount=True,
                items=[
                    FeedbackItem(member_id=member_id, dish_name="番茄炒蛋"),  # 不填分量 -> 复用 AI 推荐
                ],
            )
        )
        assert count == 1
        rows = svc.list_feedback(1, date(2026, 9, 21), date(2026, 9, 27))
        assert rows[0].is_ai_recommended == 1
        assert rows[0].amount_g == Decimal("150")

    def test_invalid_member_skipped(self, db):
        _add_member(db)
        svc = FeedbackService(db)
        with pytest.raises(ValueError):
            svc.create_feedback(
                FeedbackCreate(
                    family_id=1,
                    eaten_date=date(2026, 9, 25),
                    items=[FeedbackItem(member_id=999, dish_name="番茄炒蛋", amount_g=Decimal("10"))],
                )
            )


class TestBuildReport:
    def test_report_with_feedback(self, db):
        member_id = _add_member(db)
        _generate_record(db)
        FeedbackService(db).create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),
                items=[
                    FeedbackItem(member_id=member_id, dish_name="番茄炒蛋", amount_g=Decimal("150")),
                ],
            )
        )
        svc = ReportService(db)
        report = svc.build_report(1, date(2026, 9, 21), date(2026, 9, 27))
        assert report["week_start"] == "2026-09-21"
        assert report["week_end"] == "2026-09-27"
        assert report["effective_days"] == 1
        assert len(report["members"]) == 1
        assert report["members"][0]["member_name"] == "小美"
        nutrients = report["members"][0]["nutrients"]
        assert any(n["nutrient_code"] == "protein" for n in nutrients)

    def test_report_no_feedback_raises(self, db):
        _add_member(db)
        svc = ReportService(db)
        with pytest.raises(ReportNotReady):
            svc.build_report(1, date(2026, 9, 21), date(2026, 9, 27))

    def test_save_and_list(self, db):
        member_id = _add_member(db)
        _generate_record(db)
        FeedbackService(db).create_feedback(
            FeedbackCreate(
                family_id=1,
                eaten_date=date(2026, 9, 25),
                items=[
                    FeedbackItem(member_id=member_id, dish_name="番茄炒蛋", amount_g=Decimal("150")),
                ],
            )
        )
        svc = ReportService(db)
        data = svc.build_report(1, date(2026, 9, 21), date(2026, 9, 27))
        report = svc.save_report(1, date(2026, 9, 21), date(2026, 9, 27), data)
        assert report.id > 0
        assert len(svc.list_reports(1)) == 1