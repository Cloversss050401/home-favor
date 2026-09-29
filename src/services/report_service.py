"""周度营养报告业务。

对齐硬性业务规则第 4 条：
- 菜品→食材分解→查成分表→单餐营养→按天累加→按周聚合（周一~周日）
- 只统计有反馈记录的天数，空白日期不做 AI 估算
- 超标判定：实际摄入 > 1.2 × RNI
- 周达标率 = 周实际总摄入 / (RNI × 有效统计天数) × 100%
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.config.constants import CORE_NUTRIENTS, EXCEED_RATIO, NUTRIENT_LABEL_CN
from src.exceptions.business_exception import ReportNotReady
from src.models.feedback_model import UserFeedback
from src.models.report_model import WeeklyNutReport
from src.repository.feedback_repo import FeedbackRepo
from src.repository.member_repo import MemberRepo
from src.repository.report_repo import ReportRepo
from src.repository.recipe_record_repo import RecipeRecordRepo
from src.services.nutrition_service import NutritionService
from src.utils.date_util import date_list


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback_repo = FeedbackRepo(db)
        self.member_repo = MemberRepo(db)
        self.record_repo = RecipeRecordRepo(db)
        self.report_repo = ReportRepo(db)
        self.nutrition = NutritionService(db)

    # ---------- 聚合计算 ----------
    def _intake_for_member(
        self, feedback_rows: list[UserFeedback], member_id: int
    ) -> dict[date, dict[str, Decimal]]:
        """单成员逐日营养摄入（按天累加）。"""
        daily: dict[date, dict[str, Decimal]] = {}
        for row in feedback_rows:
            if row.member_id != member_id:
                continue
            record = self.record_repo.get(row.recipe_record_id) if row.recipe_record_id else None
            intake = self.nutrition.decompose_dish(row.dish_name, row.amount_g, record)
            day = daily.setdefault(row.eaten_date, {})
            for nut, val in intake.items():
                day[nut] = day.get(nut, Decimal("0")) + Decimal(str(val))
        return daily

    def build_report(
        self, family_id: int, week_start: date, week_end: date
    ) -> dict:
        """生成周报数据字典（不落库，由调用方决定落库）。"""
        members = self.member_repo.list_active(family_id)
        feedback_rows = self.feedback_repo.list_by_range(family_id, week_start, week_end)
        if not feedback_rows:
            raise ReportNotReady()

        effective = len(
            {r.eaten_date for r in feedback_rows}
        )  # 有反馈记录的天数
        days = [d for d in date_list(week_start, week_end)]
        member_summaries = []
        all_tips: list[str] = []

        for member in members:
            daily = self._intake_for_member(feedback_rows, member.id)
            # 只统计有记录的天数
            recorded_days = [d for d in days if d in daily]
            if not recorded_days:
                continue
            nutrients_summary = []
            for nut in CORE_NUTRIENTS:
                rni = self.nutrition.daily_rni(member, nut)
                if rni is None:
                    continue
                total = sum(
                    (daily[d].get(nut, Decimal("0")) for d in recorded_days),
                    Decimal("0"),
                )
                daily_avg = total / Decimal(len(recorded_days))
                rate = (
                    total / (rni * Decimal(len(recorded_days))) * Decimal("100")
                    if rni and len(recorded_days)
                    else Decimal("0")
                )
                exceeded = daily_avg > rni * Decimal(str(EXCEED_RATIO))
                gap = (rni - daily_avg) * Decimal(len(recorded_days))
                nutrients_summary.append(
                    {
                        "nutrient_code": nut,
                        "nutrient_name": NUTRIENT_LABEL_CN.get(nut, nut),
                        "rni_per_day": float(rni),
                        "effective_days": len(recorded_days),
                        "total_intake": round(float(total), 2),
                        "daily_avg": round(float(daily_avg), 2),
                        "rate": round(float(rate), 2),
                        "exceeded": exceeded,
                        "gap": round(float(gap if gap > 0 else 0), 2),
                    }
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
                }
            )
            all_tips.extend(problem)

        if not member_summaries:
            raise ReportNotReady("本周无有效成员反馈记录，无法生成周报")

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "effective_days": effective,
            "members": member_summaries,
            "weekly_tips": (self._tips(all_tips) or ["下周继续保持规律饮食与运动"]),
        }

    @staticmethod
    def _tips(problems: list[str]) -> list[str]:
        """简单转成建议（二期接入 LLM 生成个性化建议）。"""
        seen = []
        for p in problems:
            if p not in seen:
                seen.append(p)
        return [f"建议关注：{p}" for p in seen[:5]]

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