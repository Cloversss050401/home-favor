"""DRIs 参考摄入量仓库：纯数据存取；配合 Redis 缓存供营养计算高频读取。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.nutrition.models import DrisStandard


class DrisRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(
        self, target_type: str, nutrient_code: str
    ) -> DrisStandard | None:
        stmt = select(DrisStandard).where(
            DrisStandard.target_type == target_type,
            DrisStandard.nutrient_code == nutrient_code,
        )
        return self.db.scalars(stmt).first()

    def list_by_target(self, target_type: str) -> list[DrisStandard]:
        stmt = select(DrisStandard).where(
            DrisStandard.target_type == target_type
        )
        return list(self.db.scalars(stmt))

    def upsert(self, rows: list[dict]) -> None:
        """批量导入数据（DRIs 初始化）。"""
        for row in rows:
            existing = self.get(row["target_type"], row["nutrient_code"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
                self.db.add(existing)
            else:
                self.db.add(DrisStandard(**row))
        self.db.commit()


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.nutrition.models import FoodNutrition


class FoodNutritionRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, food_name: str) -> FoodNutrition | None:
        stmt = select(FoodNutrition).where(
            FoodNutrition.food_name == food_name
        )
        return self.db.scalars(stmt).first()

    def get_by_names(self, names: list[str]) -> list[FoodNutrition]:
        stmt = select(FoodNutrition).where(FoodNutrition.food_name.in_(names))
        return list(self.db.scalars(stmt))

    def all(self) -> list[FoodNutrition]:
        return list(self.db.scalars(select(FoodNutrition)))

    def upsert(self, rows: list[dict]) -> None:
        """批量导入数据（食物成分表初始化）。"""
        for row in rows:
            existing = self.get_by_name(row["food_name"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
                self.db.add(existing)
            else:
                self.db.add(FoodNutrition(**row))
        self.db.commit()


from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.nutrition.models import UserFeedback


class FeedbackRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(self, items: list[UserFeedback]) -> int:
        self.db.add_all(items)
        self.db.commit()
        return len(items)

    def list_by_range(
        self, family_id: int, start: date, end: date
    ) -> list[UserFeedback]:
        stmt = (
            select(UserFeedback)
            .where(
                UserFeedback.family_id == family_id,
                UserFeedback.eaten_date >= start,
                UserFeedback.eaten_date <= end,
            )
            .order_by(UserFeedback.eaten_date.asc(), UserFeedback.member_id.asc())
        )
        return list(self.db.scalars(stmt))

    def list_dates_in_range(
        self, family_id: int, start: date, end: date
    ) -> set[date]:
        """统计有效反馈日期集合（周报只统计有记录的天数）。"""
        stmt = select(UserFeedback.eaten_date).where(
            UserFeedback.family_id == family_id,
            UserFeedback.eaten_date >= start,
            UserFeedback.eaten_date <= end,
        )
        return {row for row in self.db.scalars(stmt)}


from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.nutrition.models import WeeklyNutReport


class ReportRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: WeeklyNutReport) -> WeeklyNutReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get(self, report_id: int) -> WeeklyNutReport | None:
        return self.db.get(WeeklyNutReport, report_id)

    def list_by_family(
        self, family_id: int, limit: int = 20
    ) -> list[WeeklyNutReport]:
        stmt = (
            select(WeeklyNutReport)
            .where(WeeklyNutReport.family_id == family_id)
            .order_by(WeeklyNutReport.week_start.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def latest(self, family_id: int) -> WeeklyNutReport | None:
        stmt = (
            select(WeeklyNutReport)
            .where(WeeklyNutReport.family_id == family_id)
            .order_by(WeeklyNutReport.week_start.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def delete(self, report_id: int) -> bool:
        """物理删除一条周报记录；不存在返回 False。"""
        report = self.db.get(WeeklyNutReport, report_id)
        if report is None:
            return False
        self.db.delete(report)
        self.db.commit()
        return True
