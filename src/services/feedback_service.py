"""用户反馈业务：录入、一键全选、折算。

对齐硬性业务规则第 4 条：
- 勾选实际制作菜品 + 各成员食用分量
- 一键全选：复用 AI 推荐分配分量；手动输入优先级更高
- 菜品按自建菜谱库分解原始食材 → 查食物成分表 → 单餐营养
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.exceptions.business_exception import RecipeRecordNotFound
from src.models.feedback_model import UserFeedback
from src.repository.feedback_repo import FeedbackRepo
from src.repository.member_repo import MemberRepo
from src.repository.recipe_record_repo import RecipeRecordRepo
from src.schemas.feedback_schema import FeedbackCreate, FeedbackItem


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback_repo = FeedbackRepo(db)
        self.member_repo = MemberRepo(db)
        self.record_repo = RecipeRecordRepo(db)

    def create_feedback(self, payload: FeedbackCreate) -> int:
        """存储反馈明细。

        - 手动输入 item（amount_g 有值）优先级更高，直接存储；
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
            if it.amount_g is None:
                continue  # 手动输入项必须带分量
            manual.setdefault(it.member_id, []).append((it.dish_name, it.amount_g))

        rows: list[UserFeedback] = []
        valid_members = {m.id for m in self.member_repo.list_active(payload.family_id)}
        for item in payload.items:
            if item.member_id not in valid_members:
                continue
            # 手动输入优先；否则一键全选回填
            dish_name = item.dish_name
            amount: Decimal | None = item.amount_g
            is_ai = 0
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